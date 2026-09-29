// Offline transformation only: no Desktop modules are imported or executed.
import { readFile, writeFile, mkdir, cp } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { appendMembers, patchManager, sha256 } from './archive.mjs';

const sourceDirectory = dirname(fileURLToPath(import.meta.url));
const [pristineArgument, outputArgument] = process.argv.slice(2);
if (!pristineArgument || !outputArgument || process.argv.length !== 4)
  throw new Error('usage: build-candidate.mjs PRISTINE_ASAR NEW_OUTPUT_DIRECTORY');
const pristinePath = resolve(pristineArgument);
const outputDirectory = resolve(outputArgument);
const esbuild = await import(process.env.PROBE_ESBUILD);
const asar = await import(process.env.PROBE_ASAR_READER);
if (esbuild.version !== '0.28.2') throw new Error('unassessed bundler version');

const patchBytes = await readFile(join(sourceDirectory, 'manager-patch.json'));
const patch = JSON.parse(patchBytes);
if (patch.schema !== 'provingkit.desktop-manager-patch.v1') throw new Error('unassessed patch schema');
const pristine = await readFile(pristinePath);
if (sha256(pristine) !== patch.archiveSha256) throw new Error('unassessed pristine archive');
const manager = asar.extractFile(pristinePath, patch.target.path);
if (manager.includes(Buffer.from('PROVINGKIT_OBSERVER_278')))
  throw new Error('manager identifier collision');
const patched = patchManager(manager, {
  sourceSha256: patch.target.sha256,
  replacements: patch.replacements,
});
const bundled = await esbuild.build({
  absWorkingDir: sourceDirectory,
  entryPoints: ['desktop-adapter.mjs'],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node22',
  write: false,
  minify: false,
  metafile: true,
});
const sidecar = Buffer.from(bundled.outputFiles[0].contents);
const inputNames = Object.keys(bundled.metafile.inputs).sort();
if (JSON.stringify(inputNames) !== JSON.stringify(['desktop-adapter.mjs', 'observer-probe.mjs']))
  throw new Error('unexpected bundle inputs');
const candidate = appendMembers(pristine, {
  expectedSha256: patch.archiveSha256,
  replacements: { [patch.target.path]: patched },
  additions: { '.vite/build/desktopRuntimeObserver.js': sidecar },
});

// A failed build leaves its new staging directory for diagnosis; never overwrites one.
await mkdir(outputDirectory, { mode: 0o700 });
for (const [name, bytes] of Object.entries({
  'candidate.asar': candidate,
  'desktopRuntimeObserver.js': sidecar,
  'manager.js': patched,
})) await writeFile(join(outputDirectory, name), bytes, { flag: 'wx', mode: 0o600 });
await cp(`${pristinePath}.unpacked`, join(outputDirectory, 'candidate.asar.unpacked'), {
  recursive: true,
  errorOnExist: true,
  force: false,
});
const sourceInputs = {};
for (const name of [...inputNames, 'manager-patch.json', 'archive.mjs', 'build-candidate.mjs'])
  sourceInputs[name] = sha256(await readFile(join(sourceDirectory, name)));
const receipt = {
  schema: 'provingkit.desktop-probe-build.v1',
  bundler: { name: 'esbuild', version: esbuild.version },
  sourceInputs,
  pristineSha256: sha256(pristine),
  candidateSha256: sha256(candidate),
  sidecarSha256: sha256(sidecar),
  managerSha256: sha256(patched),
  runtimeExecuted: false,
};
await writeFile(join(outputDirectory, 'build-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`, {
  flag: 'wx', mode: 0o600,
});
console.log(JSON.stringify(receipt));
