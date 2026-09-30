import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  chmod,
  mkdir,
  mkdtemp,
  readFile,
  readlink,
  realpath,
  rm,
  stat,
  symlink,
  writeFile,
} from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

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

const shellRouteBegin = '# BEGIN check_reviewed_shell_route\n';
const shellRouteEnd = '# END check_reviewed_shell_route\n';
const shellRouteBeginAt = runbook.indexOf(shellRouteBegin);
const shellRouteEndAt = runbook.indexOf(
  shellRouteEnd,
  shellRouteBeginAt + shellRouteBegin.length,
);

if (
  shellRouteBeginAt === -1 ||
  shellRouteEndAt === -1 ||
  runbook.indexOf(
    shellRouteBegin,
    shellRouteBeginAt + shellRouteBegin.length,
  ) !== -1 ||
  runbook.indexOf(
    shellRouteEnd,
    shellRouteEndAt + shellRouteEnd.length,
  ) !== -1
) {
  throw new Error('check_reviewed_shell_route boundaries must be unique');
}

const shellRouteSource = runbook.slice(
  shellRouteBeginAt + shellRouteBegin.length,
  shellRouteEndAt,
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
PROBE_SHELL=/usr/bin/zsh
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

const expectedShellBinding = async resolvedPath => {
  const metadata = await stat(resolvedPath, { bigint: true });
  const bytes = await readFile(resolvedPath);

  return {
    resolvedPath,
    stat: [
      metadata.dev,
      metadata.ino,
      metadata.uid,
      metadata.gid,
      (metadata.mode & 0o7777n).toString(8),
      metadata.nlink,
      metadata.size,
    ].join(':'),
    sha256: createHash('sha256').update(bytes).digest('hex'),
  };
};

const invokeShellRoute = (
  shellPath,
  expected,
  mutation = 'none',
  {
    commandPath = '/usr/bin:/bin',
    extraEnvironment = {},
  } = {},
) => {
  const program = `
set -euo pipefail
export LC_ALL=C
PROBE_SHELL="$1"
PROBE_SHELL_RESOLVED="$2"
PROBE_SHELL_STAT="$3"
PROBE_SHELL_SHA256="$4"
PROBE_SHELL_ROUTE_CONTRACT="$5"
mutation="$6"
${shellRouteSource}

case "$mutation" in
  none) ;;
  resolved) PROBE_SHELL_RESOLVED=/synthetic/different ;;
  stat) PROBE_SHELL_STAT=0:0:0:0:755:1:0 ;;
  executable-digest)
    PROBE_SHELL_SHA256="$(printf '0%.0s' {1..64})"
    ;;
  route-contract)
    PROBE_SHELL_ROUTE_CONTRACT=synthetic-different
    ;;
  *) exit 97 ;;
esac

check_reviewed_shell_route
`;
  const result = spawnSync(
    '/usr/bin/bash',
    [
      '--noprofile',
      '--norc',
      '-c',
      program,
      'shell-route-test',
      shellPath,
      expected.resolvedPath,
      expected.stat,
      expected.sha256,
      'linux-system-shell-v1',
      mutation,
    ],
    {
      encoding: 'utf8',
      env: {
        LC_ALL: 'C',
        PATH: commandPath,
        ...extraEnvironment,
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

const assertShellRouteAccepted = (
  name,
  shellPath,
  expected,
  mutation = 'none',
) => {
  const result = invokeShellRoute(
    shellPath,
    expected,
    mutation,
  );
  assert.equal(
    result.status,
    0,
    `${name} was rejected\n${resultDetail(result)}`,
  );
};

const assertShellRouteRejected = (
  name,
  shellPath,
  expected,
  mutation = 'none',
) => {
  const result = invokeShellRoute(
    shellPath,
    expected,
    mutation,
  );
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
    'SHELL=/usr/bin/zsh',
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
    'SHELL',
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

  for (const [name, shell] of [
    ['empty SHELL', ''],
    ['relative SHELL', 'usr/bin/zsh'],
    ['different absolute SHELL', '/usr/bin/bash'],
    ['SHELL containing LF', '/usr/bin/zsh\n'],
    ['SHELL containing CR', '/usr/bin/zsh\r'],
  ]) {
    assertRejected(
      name,
      valid.map(entry =>
        entry.startsWith('SHELL=') ? `SHELL=${shell}` : entry,
      ),
    );
  }

  for (const kdeSessionVersion of ['5', '6']) {
    assertAccepted(
      `KDE_SESSION_VERSION=${kdeSessionVersion}`,
      [...valid, `KDE_SESSION_VERSION=${kdeSessionVersion}`].sort(),
    );
  }

  for (const kdeSessionVersion of ['', '4', '06', ' 6', '6 ', '7']) {
    assertRejected(
      `unsupported KDE_SESSION_VERSION=${JSON.stringify(kdeSessionVersion)}`,
      [...valid, `KDE_SESSION_VERSION=${kdeSessionVersion}`].sort(),
    );
  }

  const kde6 = [...valid, 'KDE_SESSION_VERSION=6'].sort();
  assertRejected(
    'present KDE selector with digest for its absence',
    kde6,
    environmentDigest(valid),
  );

  const withoutShell = valid.filter(
    entry => !entry.startsWith('SHELL='),
  );
  assertRejected(
    'complete environment with digest computed without SHELL',
    valid,
    environmentDigest(withoutShell),
  );

  const duplicate = [...valid];
  duplicate.splice(
    duplicate.indexOf('HOME=/synthetic/home') + 1,
    0,
    'HOME=/synthetic/home',
  );
  assertRejected('duplicate name', duplicate);

  const duplicateShell = [...valid];
  duplicateShell.splice(
    duplicateShell.indexOf('SHELL=/usr/bin/zsh') + 1,
    0,
    'SHELL=/usr/bin/zsh',
  );
  assertRejected('duplicate SHELL', duplicateShell);

  const duplicateKde = [
    ...valid,
    'KDE_SESSION_VERSION=6',
    'KDE_SESSION_VERSION=6',
  ].sort();
  assertRejected(
    'duplicate KDE_SESSION_VERSION',
    duplicateKde,
  );

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
    'CLAUDE_USER_DATA_DIR=/synthetic/override',
    'CHROME_DESKTOP=synthetic.desktop',
    'ELECTRON_FORCE_IS_PACKAGED=true',
    'ELECTRON_RUN_AS_NODE=1',
    'LD_PRELOAD=/synthetic/library.so',
    'NODE_OPTIONS=--require=/synthetic/module.cjs',
    'PROVINGKIT_OBSERVER_CONFIG=/synthetic/config.json',
    'QT_PLUGIN_PATH=/synthetic/plugins',
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

test('reviewed shell executable route validation', async () => {
  const bashBinding = await expectedShellBinding(
    '/usr/bin/bash',
  );

  assertShellRouteAccepted(
    'root-owned /bin alias route',
    '/bin/sh',
    bashBinding,
  );

  for (const [name, mutation] of [
    ['changed resolved path', 'resolved'],
    ['changed executable identity', 'stat'],
    ['changed executable digest', 'executable-digest'],
    ['changed route contract', 'route-contract'],
  ]) {
    assertShellRouteRejected(
      name,
      '/bin/sh',
      bashBinding,
      mutation,
    );
  }

});

test('root-owned non-shell executable is rejected', async () => {
  const trueBinding = await expectedShellBinding(
    '/usr/bin/true',
  );
  assertShellRouteRejected(
    'root-owned non-shell executable',
    '/usr/bin/true',
    trueBinding,
  );
});

test(
  'LF-bearing symlink target is preserved and rejected',
  async () => {
    const fixtureRoot = await mkdtemp(
      join(tmpdir(), 'provingkit-shell-route-'),
    );
    const modelUsrBin = join(fixtureRoot, 'usr', 'bin');
    const modelTarget = join(modelUsrBin, 'bash\n');
    const modelShell = join(modelUsrBin, 'sh');
    const shimDirectory = join(fixtureRoot, 'shim');
    const readlinkShim = join(shimDirectory, 'readlink');
    const tracePath = join(fixtureRoot, 'readlink.trace');

    try {
      await mkdir(modelUsrBin, { recursive: true });
      await mkdir(shimDirectory, { recursive: true });
      await writeFile(
        modelTarget,
        'synthetic LF-bearing shell target\n',
        { mode: 0o755 },
      );
      await chmod(modelTarget, 0o755);
      await symlink('bash\n', modelShell);

      assert.equal(await readlink(modelShell), 'bash\n');
      assert.equal(await realpath(modelShell), modelTarget);

      await writeFile(tracePath, '');

      await writeFile(
        readlinkShim,
        `#!/usr/bin/bash
set -euo pipefail

canonical=0
no_newline=0
path=

for arg in "$@"; do
  case "$arg" in
    --)
      ;;
    -e|--canonicalize-existing)
      canonical=1
      ;;
    -n|--no-newline)
      no_newline=1
      ;;
    -*)
      if [[ "$arg" == -*e* ]]; then
        canonical=1
      fi
      if [[ "$arg" == -*n* ]]; then
        no_newline=1
      fi
      ;;
    *)
      path="$arg"
      ;;
  esac
done

case "$path" in
  /bin/sh|/usr/bin/sh)
    printf 'leaf:%s:%s\\n' \
      "$canonical" \
      "$no_newline" >> "$SYNTHETIC_TRACE"
    if ((canonical)); then
      printf '/usr/bin/'
    fi
    /usr/bin/readlink -n -- "$SYNTHETIC_SH"
    if ((!no_newline)); then
      printf '\\n'
    fi
    ;;
  *)
    exec /usr/bin/readlink "$@"
    ;;
esac
`,
        { mode: 0o755 },
      );
      await chmod(readlinkShim, 0o755);

      const bashBinding = await expectedShellBinding(
        '/usr/bin/bash',
      );
      const result = invokeShellRoute(
        '/bin/sh',
        bashBinding,
        'none',
        {
          commandPath: `${shimDirectory}:/usr/bin:/bin`,
          extraEnvironment: {
            SYNTHETIC_SH: modelShell,
            SYNTHETIC_TRACE: tracePath,
          },
        },
      );
      const trace = await readFile(tracePath, 'utf8');

      assert.match(trace, /^leaf:0:[01]$/m);
      assert.notEqual(
        result.status,
        0,
        `LF-bearing symlink target was accepted\n${resultDetail(result)}`,
      );
    } finally {
      await rm(fixtureRoot, {
        recursive: true,
        force: true,
      });
    }
  },
);
