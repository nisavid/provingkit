// Synthetic Desktop/query adapter. Never imports or contacts a harness.
export function createFixture() {
  const binding = { taskId: 'fixture-task', codeSessionId: 'fixture-code-a', appStartId: 'fixture-boot', generation: 1 };
  const record = {
    ...binding, inputStream: {}, turn: 'idle',
    host: {
      spawnRoute: { accountUuid: 'fixture-account', orgId: 'fixture-org' },
      permissionMode: 'default', harnessCwd: '/fixture/worktree',
      alwaysAllowedReasons: [], cuAllowedApps: [], cuGrantFlags: { clipboardRead: false, clipboardWrite: false, systemKeyCombos: false },
      effectiveCuAllowedApps: [], effectiveCuGrantFlags: { clipboardRead: false, clipboardWrite: false, systemKeyCombos: false },
      sessionPermissionUpdates: [], flagScopeSyncPending: false, modeRequestsInFlight: 0,
    },
  };
  const state = { record, binding, queryCalls: [], releases: [] };
  const query = {
    async accountInfo() { state.queryCalls.push('accountInfo'); return { apiProvider: 'firstParty', tokenSource: 'fixture' }; },
    async getContextUsage() { state.queryCalls.push('getContextUsage'); return { model: 'fixture-model-a', unrelated: 'omit me' }; },
    async listPermissionRules() {
      state.queryCalls.push('listPermissionRules');
      return { state: { rules: [{ behavior: 'allow', source: 'session', rule: 'Read(/fixture/**)', editability: 'session' }], workspaceDirectories: [{ path: '/fixture', source: 'session' }], originalCwd: '/fixture/original', managedOnly: false } };
    },
  };
  record.query = query;
  state.selectReceiver = (taskId) => state.record?.taskId === taskId ? state.record : null;
  state.replaceQuery = () => { record.query = { ...query }; record.generation += 1; record.codeSessionId = 'fixture-code-b'; };
  state.delayModel = () => { query.getContextUsage = () => new Promise(resolve => state.releases.push(() => resolve({ model: 'late-model' }))); };
  state.releaseLate = () => { for (const release of state.releases.splice(0)) release(); };
  return state;
}
