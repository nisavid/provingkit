import test from 'node:test';
import assert from 'node:assert/strict';
import {
  appendFile,
  mkdtemp,
  mkdir,
  writeFile,
  readFile,
  rm,
  cp,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { appendMembers, patchManager } from './archive.mjs';
import {
  assessBuildDependencies,
  loadAssessedArchiveReader,
} from './build-dependency-identity.mjs';

const buildDependencyOptions = {
  manifestUrl: new URL(
    './build-dependency-manifest.json',
    import.meta.url,
  ),
  archiveReaderUrl: process.env.PROBE_ASAR_READER,
  bundlerUrl: process.env.PROBE_ESBUILD,
};

// The caller supplies the selected independently installed tool closure.
const { archiveReader: asar } =
  await loadAssessedArchiveReader(buildDependencyOptions);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

test('build dependency assessment rejects selected package drift', async () => {
  const directory = await mkdtemp(
    join(tmpdir(), 'observer-build-dependencies-'),
  );

  try {
    const manifestBytes = await readFile(
      buildDependencyOptions.manifestUrl,
    );
    const manifest = JSON.parse(manifestBytes);
    const copiedNodeModules = join(directory, 'node_modules');
    const copiedManifest = join(
      directory,
      'build-dependency-manifest.json',
    );
    await mkdir(copiedNodeModules);
    await writeFile(copiedManifest, manifestBytes);

    const selectedGroups = [
      {
        name: 'archiveReader',
        entrypoint: 'lib/asar.js',
        url: process.env.PROBE_ASAR_READER,
      },
      {
        name: 'bundler',
        entrypoint: 'lib/main.js',
        url: process.env.PROBE_ESBUILD,
      },
    ];

    for (const selected of selectedGroups) {
      const group = manifest[selected.name];
      const entryPackage = group.packages.find(
        packageRecord =>
          packageRecord.name === group.entryPackage,
      );
      let installedNodeModules = fileURLToPath(selected.url);
      for (
        let index = 0;
        index <
          entryPackage.relativeRoot.split('/').length +
          selected.entrypoint.split('/').length;
        index += 1
      ) {
        installedNodeModules = dirname(installedNodeModules);
      }

      for (const packageRecord of group.packages) {
        const destination = join(
          copiedNodeModules,
          ...packageRecord.relativeRoot.split('/'),
        );
        await mkdir(dirname(destination), { recursive: true });
        await cp(
          join(
            installedNodeModules,
            ...packageRecord.relativeRoot.split('/'),
          ),
          destination,
          {
            recursive: true,
            errorOnExist: true,
            force: false,
          },
        );
      }
    }

    const copiedOptions = {
      manifestUrl: pathToFileURL(copiedManifest),
      archiveReaderUrl: pathToFileURL(join(
        copiedNodeModules,
        '@electron',
        'asar',
        'lib',
        'asar.js',
      )).href,
      bundlerUrl: pathToFileURL(join(
        copiedNodeModules,
        'esbuild',
        'lib',
        'main.js',
      )).href,
    };
    const identity = await assessBuildDependencies(copiedOptions);

    assert.equal(identity.manifestSha256, sha(manifestBytes));
    assert.equal(identity.archiveReader.name, '@electron/asar');
    assert.equal(identity.archiveReader.version, '4.3.0');
    assert.equal(
      identity.bundler.executable.sha256,
      manifest.bundler.packages
        .find(item => item.name === '@esbuild/linux-x64')
        .files['bin/esbuild'],
    );

    const rejectDrift = async (relativePath, addition) => {
      const path = join(
        copiedNodeModules,
        ...relativePath.split('/'),
      );
      const original = await readFile(path);
      try {
        await appendFile(path, addition);
        await assert.rejects(
          assessBuildDependencies(copiedOptions),
          /unassessed build dependency identity/,
        );
      } finally {
        await writeFile(path, original);
      }
    };

    await rejectDrift('esbuild/lib/main.js', '\n');
    await rejectDrift(
      '@esbuild/linux-x64/bin/esbuild',
      Buffer.from([0]),
    );
    await rejectDrift('glob/dist/commonjs/index.js', '\n');
    await rejectDrift('@electron/asar/lib/asar.js', '\n');
  } finally {
    await rm(directory, {
      recursive: true,
      force: true,
    });
  }
});

test('a manager patch applies only to its inspected source and unique nonoverlapping anchors', () => {
  const source = Buffer.from('"use strict";function example(){return 1;}');
  const patch = { sourceSha256: sha(source), replacements: [
    { before: '"use strict";', after: '"use strict";const fixture = true;' },
    { before: 'return 1;', after: 'return 2;' },
  ] };
  assert.equal(patchManager(source, patch).toString(),
    '"use strict";const fixture = true;function example(){return 2;}');
  assert.equal(source.toString(), '"use strict";function example(){return 1;}');
  assert.throws(() => patchManager(Buffer.from('changed'), patch), /unassessed/);
  assert.throws(() => patchManager(source, { ...patch,
    replacements: [{ before: 'absent', after: 'x' }] }), /unique/);
  assert.throws(() => patchManager(source, { ...patch,
    replacements: [{ before: ';', after: 'x' }] }), /unique/);
  assert.throws(() => patchManager(source, { ...patch,
    replacements: [{ before: 'return 1;', after: 'x' }, { before: '1;', after: 'y' }] }), /overlap/);
});

test('the authored manager loader is inert when inactive and isolates configured sidecar loading', async () => {
  const patch = JSON.parse(
    await readFile(new URL('./manager-patch.json', import.meta.url)),
  );
  const insertion = patch.replacements.find(
    replacement => replacement.purpose === 'require-insertion',
  );
  const suffix = '(function(){try';
  const suffixAt = insertion.after.indexOf(suffix);

  assert.ok(suffixAt > 0);

  const fragment = insertion.after.slice(
    '"use strict";'.length,
    suffixAt,
  );
  const expectedFunctions = [
    'noteQueryInstalled',
    'teardownQuery',
    'noteCodeSessionId',
    'recordModeEvent',
    'bootDesktopObserver',
  ];

  const evaluate = ({
    configured,
    resolveError,
    loadError,
    loaded,
  }) => {
    const calls = [];
    const syntheticRequire = specifier => {
      calls.push(['require', specifier]);
      if (loadError) throw loadError;
      return loaded;
    };

    syntheticRequire.resolve = specifier => {
      calls.push(['resolve', specifier]);
      if (resolveError) throw resolveError;
      return '/fixture/desktopRuntimeObserver.js';
    };

    const adapter = Function(
      'require',
      'process',
      `${fragment}\nreturn PROVINGKIT_OBSERVER_278;`,
    )(
      syntheticRequire,
      {
        env: configured
          ? { PROVINGKIT_OBSERVER_CONFIG: '/fixture/config.json' }
          : {},
      },
    );

    return { adapter, calls };
  };

  const inactive = evaluate({ configured: false });
  assert.deepEqual(inactive.calls, []);
  assert.equal(inactive.adapter.modulePath, null);
  assert.ok(
    expectedFunctions.every(
      name => inactive.adapter[name]() === false,
    ),
  );

  const failed = evaluate({
    configured: true,
    loadError: new Error('synthetic load failure'),
  });
  assert.deepEqual(failed.calls, [
    ['resolve', './desktopRuntimeObserver.js'],
    ['require', '/fixture/desktopRuntimeObserver.js'],
  ]);
  assert.equal(failed.adapter.modulePath, null);
  assert.ok(
    expectedFunctions.every(name => failed.adapter[name]() === false),
  );

  const loaded = Object.fromEntries(
    expectedFunctions.map(name => [name, () => name]),
  );
  const accepted = evaluate({ configured: true, loaded });
  assert.equal(
    accepted.adapter.modulePath,
    '/fixture/desktopRuntimeObserver.js',
  );
  assert.deepEqual(
    expectedFunctions.map(name => accepted.adapter[name]),
    expectedFunctions.map(name => loaded[name]),
  );
});

test('a copied archive changes only selected members and remains readable by Electron tooling', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'observer-archive-'));
  try {
    const tree = join(directory, 'tree');
    await mkdir(join(tree, 'nested'), { recursive: true });
    await writeFile(join(tree, 'keep.txt'), 'unchanged');
    await writeFile(join(tree, 'nested', 'manager.js'), 'old manager');
    const pristinePath = join(directory, 'pristine.asar');
    await asar.createPackage(tree, pristinePath);
    const pristine = await readFile(pristinePath);
    const candidate = appendMembers(pristine, {
      expectedSha256: sha(pristine),
      replacements: { 'nested/manager.js': Buffer.from('new manager') },
      additions: { 'nested/observer.js': Buffer.from('observer') },
    });
    const candidatePath = join(directory, 'candidate.asar');
    await writeFile(candidatePath, candidate, { flag: 'wx' });
    assert.equal(asar.extractFile(candidatePath, 'keep.txt').toString(), 'unchanged');
    assert.equal(asar.extractFile(candidatePath, 'nested/manager.js').toString(), 'new manager');
    assert.equal(asar.extractFile(candidatePath, 'nested/observer.js').toString(), 'observer');
    const before = asar.getRawHeader(pristinePath).header;
    const after = asar.getRawHeader(candidatePath).header;
    assert.deepEqual(after.files['keep.txt'], before.files['keep.txt']);
    assert.equal(asar.extractFile(pristinePath, 'nested/manager.js').toString(), 'old manager');
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('unpacked native assets are preserved and cannot be silently changed into packed members', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'observer-archive-'));
  try {
    const tree = join(directory, 'tree');
    await mkdir(tree);
    await writeFile(join(tree, 'manager.js'), 'old manager');
    await writeFile(join(tree, 'binding.node'), 'synthetic native asset');
    const pristinePath = join(directory, 'pristine.asar');
    await asar.createPackageWithOptions(tree, pristinePath, { unpack: '*.node' });
    const pristine = await readFile(pristinePath);
    const options = { expectedSha256: sha(pristine), replacements: { 'manager.js': Buffer.from('new manager') } };
    const candidatePath = join(directory, 'candidate.asar');
    await writeFile(candidatePath, appendMembers(pristine, options));
    await cp(`${pristinePath}.unpacked`, `${candidatePath}.unpacked`, { recursive: true });
    assert.equal(asar.extractFile(candidatePath, 'binding.node').toString(), 'synthetic native asset');
    assert.deepEqual(asar.getRawHeader(candidatePath).header.files['binding.node'],
      asar.getRawHeader(pristinePath).header.files['binding.node']);
    assert.throws(() => appendMembers(pristine, { ...options,
      replacements: { 'binding.node': Buffer.from('different') } }), /packed file/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('the builder rejects source drift and mistaken replacement or addition names', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'observer-archive-'));
  try {
    const tree = join(directory, 'tree');
    await mkdir(tree);
    await writeFile(join(tree, 'known.js'), 'original');
    const archive = join(directory, 'pristine.asar');
    await asar.createPackage(tree, archive);
    const pristine = await readFile(archive);
    assert.throws(() => appendMembers(pristine, { expectedSha256: '0'.repeat(64) }), /unassessed/);
    assert.throws(() => appendMembers(pristine, { expectedSha256: sha(pristine),
      replacements: { 'missing.js': Buffer.from('replacement') } }), /replacement/);
    assert.throws(() => appendMembers(pristine, { expectedSha256: sha(pristine),
      additions: { 'known.js': Buffer.from('addition') } }), /addition/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
