import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';

const runbook = await readFile(
  new URL('./application-operation.md', import.meta.url),
  'utf8',
);
const begin = '# BEGIN validate_reviewed_launch_environment\n';
const end = '# END validate_reviewed_launch_environment\n';
const beginAt = runbook.indexOf(begin);
const endAt = runbook.indexOf(end, beginAt + begin.length);

if (
  beginAt === -1 ||
  endAt === -1 ||
  runbook.indexOf(begin, beginAt + begin.length) !== -1 ||
  runbook.indexOf(end, endAt + end.length) !== -1
) {
  throw new Error(
    'validate_reviewed_launch_environment boundaries must be unique',
  );
}

const functionSource = runbook.slice(
  beginAt + begin.length,
  endAt,
);

const environmentDigest = entries => {
  const hash = createHash('sha256');
  for (const entry of entries) {
    hash.update(entry);
    hash.update(Buffer.from([0]));
  }
  return hash.digest('hex');
};

const invokeValidator = (
  entries,
  expectedDigest = environmentDigest(entries),
) => {
  const program = `
set -euo pipefail
export LC_ALL=C
PROBE_HOME=/synthetic/home
PROBE_PROFILE=default
PROBE_LAUNCHER=/usr/bin/claude-desktop
PROBE_LAUNCH_ENV_SHA256="$1"
shift
TEST_LAUNCH_ENV=("$@")
${functionSource}
validate_reviewed_launch_environment TEST_LAUNCH_ENV
`;
  const result = spawnSync(
    '/usr/bin/bash',
    [
      '--noprofile',
      '--norc',
      '-c',
      program,
      'launcher-input-test',
      expectedDigest,
      ...entries,
    ],
    {
      encoding: 'utf8',
      env: {
        LC_ALL: 'C',
        PATH: '/usr/bin:/bin',
      },
      timeout: 5000,
    },
  );

  assert.ifError(result.error);
  assert.equal(result.signal, null);
  assert.equal(typeof result.status, 'number');
  return result;
};

const resultDetail = result =>
  [result.stdout, result.stderr].filter(Boolean).join('\n');

const assertAccepted = (name, entries, expectedDigest) => {
  const result = invokeValidator(entries, expectedDigest);
  assert.equal(
    result.status,
    0,
    `${name} was rejected\n${resultDetail(result)}`,
  );
};

const assertRejected = (name, entries, expectedDigest) => {
  const result = invokeValidator(entries, expectedDigest);
  assert.notEqual(
    result.status,
    0,
    `${name} was accepted`,
  );
};

test('reviewed launcher environment validation', () => {
  const valid = [
    'CLAUDE_PROFILE=default',
    'DISPLAY=',
    'HOME=/synthetic/home',
    'LOGNAME=probe',
    'PATH=/usr/bin:/bin',
    'TERM=xterm=synthetic',
    'USER=probe',
  ];

  // Establish the ordinary reviewed base case before rejection controls.
  assertAccepted(
    'valid absolute PATH with empty optional and equals-sign value',
    valid,
  );

  const absentOptional = valid.filter(
    entry => entry !== 'DISPLAY=',
  );
  assert.notEqual(
    environmentDigest(valid),
    environmentDigest(absentOptional),
  );
  assertAccepted('absent optional value', absentOptional);

  for (const required of [
    'HOME',
    'USER',
    'LOGNAME',
    'PATH',
    'CLAUDE_PROFILE',
  ]) {
    assertRejected(
      `missing required ${required}`,
      valid.filter(entry => !entry.startsWith(`${required}=`)),
    );
  }

  assertRejected(
    'changed HOME binding',
    valid.map(entry =>
      entry.startsWith('HOME=')
        ? 'HOME=/synthetic/other'
        : entry,
    ),
  );
  assertRejected(
    'changed profile binding',
    valid.map(entry =>
      entry.startsWith('CLAUDE_PROFILE=')
        ? 'CLAUDE_PROFILE=named'
        : entry,
    ),
  );

  const duplicate = [...valid];
  duplicate.splice(
    duplicate.indexOf('HOME=/synthetic/home') + 1,
    0,
    'HOME=/synthetic/home',
  );
  assertRejected('duplicate name', duplicate);

  const outOfOrder = [...valid];
  const lognameAt = outOfOrder.indexOf('LOGNAME=probe');
  const pathAt = outOfOrder.indexOf('PATH=/usr/bin:/bin');
  [outOfOrder[lognameAt], outOfOrder[pathAt]] = [
    outOfOrder[pathAt],
    outOfOrder[lognameAt],
  ];
  assertRejected('out-of-order names', outOfOrder);

  for (const forbidden of [
    'CLAUDE_APP_ASAR=/synthetic/candidate.asar',
    'ELECTRON_FORCE_IS_PACKAGED=true',
    'PROVINGKIT_OBSERVER_CONFIG=/synthetic/config.json',
  ]) {
    assertRejected(
      `forbidden routing name ${forbidden.split('=', 1)[0]}`,
      [...valid, forbidden].sort(),
    );
  }

  for (const [name, path] of [
    ['empty PATH', ''],
    ['leading empty PATH component', ':/usr/bin'],
    ['trailing empty PATH component', '/usr/bin:'],
    ['doubled PATH separator', '/usr/bin::/bin'],
    ['relative PATH component', '/usr/bin:bin'],
  ]) {
    assertRejected(
      name,
      valid.map(entry =>
        entry.startsWith('PATH=') ? `PATH=${path}` : entry,
      ),
    );
  }

  assertRejected(
    'changed environment digest',
    valid,
    '0'.repeat(64),
  );
});
