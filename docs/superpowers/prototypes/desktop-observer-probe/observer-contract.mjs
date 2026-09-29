export const GETTER_SET_ID =
  'desktop-query.readonly.v1:accountInfo,getContextUsage-summary,listPermissionRules';

export const MONOTONIC_CLOCK_ID = 'linux-clock-monotonic.v1';
export const LINUX_BOOT_ID_PATH = '/proc/sys/kernel/random/boot_id';

export const SELECTED_EXECUTOR_REPORT_BASIS =
  'manager-retained-report; not independent OS association';

export const SELECTED_EXECUTOR_REPORT_KEYS = Object.freeze([
  'taskId',
  'cliPid',
  'cliPidAtMs',
  'cliReportedVersion',
  'currentCodeSessionId',
  'queryGeneration',
  'historicProvenance',
  'queryToOsAssociation',
  'reportBasis',
]);

export const CONFIG_SCHEMA = 'desktop-observer.probe-config.v1';
export const BOOTSTRAP_SCHEMA = 'desktop-observer.bootstrap.v1';
export const ARM_SCHEMA = 'desktop-observer.arm.v1';
export const SAMPLE_SCHEMA = 'desktop-observer.sample.v1';

export const MAX_CONFIG_BYTES = 4096;
export const MAX_SAMPLE_BYTES = 16 * 1024;
export const MAX_RUN_OUTPUT_BYTES = 64 * 1024;
export const MAX_SAMPLES = 3;
export const MAX_OBSERVATION_WINDOW_MS = 30_000;
export const MIN_SAMPLE_INTERVAL_MS = 5_000;
export const MAX_GETTER_TIMEOUT_MS = 2_000;
export const MAX_SETUP_DEADLINE_MS = 60_000;
export const ARM_DEADLINE_MS = 60_000;
export const MAX_ARRAY_ITEMS = 32;
export const MAX_TEXT_BYTES = 256;
export const MAX_CWD_BYTES = 1024;

export const UNKNOWN_CLAIMS = Object.freeze([
  'current-account-route',
  'current-model-freshness',
  'current-permission-mode',
  'complete-applied-permissions',
  'current-cwd',
  'native-address-binding',
  'external-delivery-and-ack',
]);

export const BINDING_KEYS = Object.freeze([
  'runId',
  'configSha256',
  'moduleSha256',
  'copiedAsarSha256',
  'appStartNonce',
  'pid',
  'processStartTicks',
  'targetTaskId',
  'targetCodeSessionId',
  'queryGeneration',
  'getterSetId',
  'monotonicClockId',
  'linuxBootId',
]);

export const ARM_KEYS = Object.freeze([
  'schema',
  ...BINDING_KEYS,
  'maxSamples',
  'minIntervalMs',
  'observationWindowMs',
  'perGetterTimeoutMs',
]);

export const HOST_KEYS = Object.freeze([
  'spawnRoute',
  'permissionMode',
  'modeEvent',
  'selectedExecutorReport',
  'harnessCwd',
  'cwdEventProvenance',
  'alwaysAllowedReasons',
  'cuAllowedApps',
  'cuGrantFlags',
  'effectiveCuAllowedApps',
  'effectiveCuGrantFlags',
  'sessionPermissionUpdateTypes',
  'flagScopeSyncPending',
  'modeRequestsInFlight',
  'pendingCoverage',
  'gaps',
]);

export const HOST_GAP_FIELDS = Object.freeze([
  'spawnRoute',
  'permissionMode',
  'modeEvent',
  'selectedExecutorReport',
  'selectedExecutorReport.taskId',
  'selectedExecutorReport.cliPid',
  'selectedExecutorReport.cliPidAtMs',
  'selectedExecutorReport.cliReportedVersion',
  'selectedExecutorReport.currentCodeSessionId',
  'harnessCwd',
  'alwaysAllowedReasons',
  'cuAllowedApps',
  'cuGrantFlags',
  'effectiveCuAllowedApps',
  'effectiveCuGrantFlags',
  'sessionPermissionUpdateTypes',
  'flagScopeSyncPending',
  'modeRequestsInFlight',
]);

export const FAILURE_CLASSES = Object.freeze([
  'unsupported',
  'unavailable',
  'limit_exceeded',
  'timeout',
  'identity_changed',
  'rejected',
  'shape_invalid',
]);

export const FAILURE_STAGES = Object.freeze([
  'accountInfo',
  'getContextUsageSummary',
  'listPermissionRules',
  'hostBefore',
  'hostAfter',
  'lifecycle',
  'publication',
  'wallClock',
]);

export const FIELD_NAMES = Object.freeze([
  'accountInfo',
  'getContextUsageSummary',
  'listPermissionRules',
  'hostBefore',
  'hostAfter',
]);
