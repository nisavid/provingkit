import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import { createRequire } from 'node:module';
import {
  basename,
  dirname,
  isAbsolute,
  join,
  relative,
  resolve,
  sep,
} from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { sha256 } from './archive.mjs';

const GROUPS = Object.freeze({
  archiveReader: Object.freeze({
    entryPackage: '@electron/asar',
    version: '4.3.0',
    entrypoint: 'lib/asar.js',
    qualification:
      'complete observed package-file inventory for the selected installed runtime dependency closure; Node and host OS are trusted baseline',
  }),
  bundler: Object.freeze({
    entryPackage: 'esbuild',
    version: '0.28.2',
    entrypoint: 'lib/main.js',
    qualification:
      'complete observed package-file inventory for the selected Linux x64 installed runtime dependency closure; Node and host OS are trusted baseline',
    executable: Object.freeze({
      packageName: '@esbuild/linux-x64',
      version: '0.28.2',
      relativePath: 'bin/esbuild',
    }),
    dependencySpecifiers: Object.freeze({
      '@esbuild/linux-x64': '@esbuild/linux-x64/bin/esbuild',
    }),
  }),
});

const MODULE_ENVIRONMENT_VARIABLES = Object.freeze([
  'ESBUILD_BINARY_PATH',
  'NODE_COMPILE_CACHE',
  'NODE_OPTIONS',
  'NODE_PATH',
  'NODE_PRESERVE_SYMLINKS',
  'NODE_PRESERVE_SYMLINKS_MAIN',
]);

const MODULE_EXEC_ARGUMENTS = Object.freeze([
  '--conditions',
  '--experimental-default-type',
  '--experimental-loader',
  '--import',
  '--loader',
  '--preserve-symlinks',
  '--preserve-symlinks-main',
  '--require',
  '-C',
  '-r',
]);

function rejectIdentity() {
  throw new Error('unassessed build dependency identity');
}

function rejectModuleEnvironment() {
  throw new Error('unassessed module environment');
}

function assessModuleEnvironment() {
  if (
    MODULE_ENVIRONMENT_VARIABLES.some(name =>
      Object.hasOwn(process.env, name),
    )
  ) {
    rejectModuleEnvironment();
  }

  if (
    process.execArgv.some(argument =>
      MODULE_EXEC_ARGUMENTS.some(option =>
        argument === option ||
        argument.startsWith(`${option}=`) ||
        (
          (option === '-r' || option === '-C') &&
          argument.startsWith(option) &&
          argument.length > option.length
        ),
      ),
    )
  ) {
    rejectModuleEnvironment();
  }
}

function assertExactKeys(value, keys) {
  if (
    value === null ||
    typeof value !== 'object' ||
    Array.isArray(value) ||
    JSON.stringify(Object.keys(value).sort()) !==
      JSON.stringify([...keys].sort())
  ) {
    rejectIdentity();
  }
}

function isClosedRelativePath(value) {
  if (
    typeof value !== 'string' ||
    value.length === 0 ||
    value.includes('\\') ||
    value.startsWith('/') ||
    value.endsWith('/')
  ) {
    return false;
  }

  return value
    .split('/')
    .every(part => part.length > 0 && part !== '.' && part !== '..');
}

function parseManifest(bytes) {
  let manifest;

  try {
    manifest = JSON.parse(bytes);
  } catch {
    rejectIdentity();
  }

  assertExactKeys(manifest, ['archiveReader', 'bundler']);

  for (const [groupName, expectedGroup] of Object.entries(GROUPS)) {
    const group = manifest[groupName];
    assertExactKeys(group, ['entryPackage', 'packages']);

    if (
      group.entryPackage !== expectedGroup.entryPackage ||
      !Array.isArray(group.packages) ||
      group.packages.length === 0
    ) {
      rejectIdentity();
    }

    const packagesByName = new Map();
    const roots = new Set();

    for (const packageRecord of group.packages) {
      assertExactKeys(packageRecord, [
        'files',
        'name',
        'relativeRoot',
        'runtimeDependencies',
        'version',
      ]);

      if (
        typeof packageRecord.name !== 'string' ||
        packageRecord.relativeRoot !== packageRecord.name ||
        !isClosedRelativePath(packageRecord.relativeRoot) ||
        typeof packageRecord.version !== 'string' ||
        packageRecord.version.length === 0 ||
        !Array.isArray(packageRecord.runtimeDependencies) ||
        packagesByName.has(packageRecord.name) ||
        roots.has(packageRecord.relativeRoot)
      ) {
        rejectIdentity();
      }

      assertExactKeys(
        packageRecord.files,
        Object.keys(packageRecord.files),
      );

      const fileNames = Object.keys(packageRecord.files);
      if (
        fileNames.length === 0 ||
        !Object.hasOwn(packageRecord.files, 'package.json') ||
        fileNames.some(name =>
          !isClosedRelativePath(name) ||
          !/^[0-9a-f]{64}$/.test(packageRecord.files[name]),
        )
      ) {
        rejectIdentity();
      }

      const dependencies = new Set(packageRecord.runtimeDependencies);
      if (
        dependencies.size !== packageRecord.runtimeDependencies.length ||
        packageRecord.runtimeDependencies.some(
          name => typeof name !== 'string' || name.length === 0,
        )
      ) {
        rejectIdentity();
      }

      packagesByName.set(packageRecord.name, packageRecord);
      roots.add(packageRecord.relativeRoot);
    }

    const entryPackage = packagesByName.get(group.entryPackage);
    if (!entryPackage || entryPackage.version !== expectedGroup.version) {
      rejectIdentity();
    }

    for (const packageRecord of group.packages) {
      if (
        packageRecord.runtimeDependencies.some(
          name => !packagesByName.has(name),
        )
      ) {
        rejectIdentity();
      }
    }

    const reached = new Set();
    const pending = [group.entryPackage];
    while (pending.length > 0) {
      const name = pending.pop();
      if (reached.has(name)) continue;
      reached.add(name);
      pending.push(...packagesByName.get(name).runtimeDependencies);
    }
    if (reached.size !== group.packages.length) rejectIdentity();

    if (expectedGroup.executable) {
      const executablePackage = packagesByName.get(
        expectedGroup.executable.packageName,
      );
      if (
        !executablePackage ||
        executablePackage.version !== expectedGroup.executable.version ||
        !Object.hasOwn(
          executablePackage.files,
          expectedGroup.executable.relativePath,
        )
      ) {
        rejectIdentity();
      }
    }
  }

  return manifest;
}

function canonicalFileLocation(value) {
  let url;
  let path;

  try {
    url = value instanceof URL ? new URL(value.href) : new URL(value);
    if (
      url.protocol !== 'file:' ||
      url.search.length !== 0 ||
      url.hash.length !== 0
    ) {
      rejectIdentity();
    }
    path = fileURLToPath(url);
    if (
      !isAbsolute(path) ||
      pathToFileURL(path).href !== url.href
    ) {
      rejectIdentity();
    }
  } catch {
    rejectIdentity();
  }

  return { path, url: pathToFileURL(path).href };
}

function nodeModulesRootFor(
  entrypointPath,
  relativeRoot,
  entrypoint,
) {
  const suffix = [
    ...relativeRoot.split('/'),
    ...entrypoint.split('/'),
  ];
  let nodeModulesRoot = entrypointPath;
  for (let index = 0; index < suffix.length; index += 1) {
    nodeModulesRoot = dirname(nodeModulesRoot);
  }

  if (
    basename(nodeModulesRoot) !== 'node_modules' ||
    join(nodeModulesRoot, ...suffix) !== entrypointPath
  ) {
    rejectIdentity();
  }

  return nodeModulesRoot;
}

async function assertCanonicalDirectory(path) {
  const descriptor = await lstat(path);
  if (
    !descriptor.isDirectory() ||
    await realpath(path) !== resolve(path)
  ) {
    rejectIdentity();
  }
}

async function regularFileInventory(directory, prefix = '') {
  const names = [];
  const entries = await readdir(directory, { withFileTypes: true });
  entries.sort((left, right) => left.name.localeCompare(right.name));

  for (const entry of entries) {
    const relativeName = prefix
      ? `${prefix}/${entry.name}`
      : entry.name;
    const path = join(directory, entry.name);

    if (entry.isSymbolicLink()) rejectIdentity();
    if (entry.isDirectory()) {
      names.push(...await regularFileInventory(path, relativeName));
    } else if (entry.isFile()) {
      names.push(relativeName);
    } else {
      rejectIdentity();
    }
  }

  return names;
}

function isWithin(root, path) {
  const fromRoot = relative(root, path);
  return (
    fromRoot.length > 0 &&
    fromRoot !== '..' &&
    !fromRoot.startsWith(`..${sep}`) &&
    !isAbsolute(fromRoot)
  );
}

async function assessGroup(groupName, group, entrypointLocation) {
  const expectedGroup = GROUPS[groupName];
  const entryPackage = group.packages.find(
    packageRecord => packageRecord.name === group.entryPackage,
  );
  const nodeModulesRoot = nodeModulesRootFor(
    entrypointLocation.path,
    entryPackage.relativeRoot,
    expectedGroup.entrypoint,
  );

  await assertCanonicalDirectory(nodeModulesRoot);
  const packageStates = new Map();

  for (const packageRecord of group.packages) {
    const packageRoot = join(
      nodeModulesRoot,
      ...packageRecord.relativeRoot.split('/'),
    );
    await assertCanonicalDirectory(packageRoot);

    const actualFiles = (
      await regularFileInventory(packageRoot)
    ).sort();
    const expectedFiles = Object.keys(packageRecord.files).sort();
    if (
      JSON.stringify(actualFiles) !== JSON.stringify(expectedFiles)
    ) {
      rejectIdentity();
    }

    let packageJsonBytes;
    for (const name of expectedFiles) {
      const path = join(packageRoot, ...name.split('/'));
      const descriptor = await lstat(path);
      if (!descriptor.isFile()) rejectIdentity();

      const bytes = await readFile(path);
      if (sha256(bytes) !== packageRecord.files[name]) {
        rejectIdentity();
      }
      if (name === 'package.json') packageJsonBytes = bytes;
    }

    let packageJson;
    try {
      packageJson = JSON.parse(packageJsonBytes);
    } catch {
      rejectIdentity();
    }
    if (
      packageJson.name !== packageRecord.name ||
      packageJson.version !== packageRecord.version
    ) {
      rejectIdentity();
    }

    packageStates.set(packageRecord.name, {
      fileNames: new Set(expectedFiles),
      packageRoot,
    });
  }

  for (const packageRecord of group.packages) {
    const source = packageStates.get(packageRecord.name);
    const requireFromPackage = createRequire(
      pathToFileURL(join(source.packageRoot, 'package.json')),
    );

    for (const dependency of packageRecord.runtimeDependencies) {
      const target = packageStates.get(dependency);
      const specifier =
        expectedGroup.dependencySpecifiers?.[dependency] ??
        dependency;
      let resolvedPath;

      try {
        resolvedPath = requireFromPackage.resolve(specifier);
      } catch {
        rejectIdentity();
      }

      if (
        await realpath(resolvedPath) !== resolve(resolvedPath) ||
        !isWithin(target.packageRoot, resolvedPath)
      ) {
        rejectIdentity();
      }

      const relativeName = relative(
        target.packageRoot,
        resolvedPath,
      ).split(sep).join('/');
      if (!target.fileNames.has(relativeName)) rejectIdentity();
    }
  }

  const entryState = packageStates.get(group.entryPackage);
  const entrypointSha256 =
    entryPackage.files[expectedGroup.entrypoint];
  if (
    !entrypointSha256 ||
    entrypointLocation.path !== join(
      entryState.packageRoot,
      ...expectedGroup.entrypoint.split('/'),
    )
  ) {
    rejectIdentity();
  }

  const identity = {
    name: entryPackage.name,
    version: entryPackage.version,
    packageJsonSha256: entryPackage.files['package.json'],
    entrypoint: expectedGroup.entrypoint,
    entrypointSha256,
    packages: group.packages.map(packageRecord => ({
      name: packageRecord.name,
      version: packageRecord.version,
      relativeRoot: packageRecord.relativeRoot,
    })),
    qualification: expectedGroup.qualification,
  };

  if (expectedGroup.executable) {
    const executablePackage = group.packages.find(
      packageRecord =>
        packageRecord.name ===
        expectedGroup.executable.packageName,
    );
    identity.executable = {
      packageName: executablePackage.name,
      version: executablePackage.version,
      relativePath: expectedGroup.executable.relativePath,
      sha256:
        executablePackage.files[
          expectedGroup.executable.relativePath
        ],
    };
  }

  return {
    entrypointUrl: entrypointLocation.url,
    identity,
  };
}

async function assessWithLocations({
  manifestUrl = new URL(
    './build-dependency-manifest.json',
    import.meta.url,
  ),
  archiveReaderUrl = process.env.PROBE_ASAR_READER,
  bundlerUrl = process.env.PROBE_ESBUILD,
} = {}) {
  assessModuleEnvironment();
  if (process.platform !== 'linux' || process.arch !== 'x64') {
    rejectIdentity();
  }

  try {
    const manifestLocation = canonicalFileLocation(manifestUrl);
    const manifestDescriptor = await lstat(manifestLocation.path);
    if (
      !manifestDescriptor.isFile() ||
      await realpath(manifestLocation.path) !==
        resolve(manifestLocation.path)
    ) {
      rejectIdentity();
    }

    const manifestBytes = await readFile(manifestLocation.path);
    const manifest = parseManifest(manifestBytes);
    const archiveReaderLocation =
      canonicalFileLocation(archiveReaderUrl);
    const bundlerLocation = canonicalFileLocation(bundlerUrl);

    const archiveReader = await assessGroup(
      'archiveReader',
      manifest.archiveReader,
      archiveReaderLocation,
    );
    const bundler = await assessGroup(
      'bundler',
      manifest.bundler,
      bundlerLocation,
    );

    return {
      entrypointUrls: {
        archiveReader: archiveReader.entrypointUrl,
        bundler: bundler.entrypointUrl,
      },
      identity: {
        manifestSha256: sha256(manifestBytes),
        archiveReader: archiveReader.identity,
        bundler: bundler.identity,
      },
    };
  } catch (error) {
    if (
      error instanceof Error &&
      (
        error.message === 'unassessed build dependency identity' ||
        error.message === 'unassessed module environment'
      )
    ) {
      throw error;
    }
    rejectIdentity();
  }
}

export async function assessBuildDependencies(options) {
  return (await assessWithLocations(options)).identity;
}

export async function loadAssessedBuildTools(options) {
  const assessed = await assessWithLocations(options);
  const [archiveReader, bundler] = await Promise.all([
    import(assessed.entrypointUrls.archiveReader),
    import(assessed.entrypointUrls.bundler),
  ]);
  return {
    archiveReader,
    bundler,
    identity: assessed.identity,
  };
}

export async function loadAssessedArchiveReader(options) {
  const assessed = await assessWithLocations(options);
  return {
    archiveReader: await import(
      assessed.entrypointUrls.archiveReader
    ),
    identity: assessed.identity,
  };
}
