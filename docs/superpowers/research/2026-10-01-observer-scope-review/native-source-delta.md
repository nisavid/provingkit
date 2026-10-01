## Offline source delta

The inspected LocalSessions paths can identify a Desktop task, but they do not hand a normal UI caller both the Desktop task ID and the Code session ID. I found no external transport address for the inspected LocalSessions binding or host-tool registration. These are static findings, limited to the four permitted extracted files.

| Path | What the inspected source establishes |
|---|---|
| `LocalSessions.start` | Calls manager `startSession`; its result `d` is used as `sessionId`. Without `typedText`, it returns `{sessionId: d}`. With `typedText`, it returns `bindChangesNamedInPrompt(d, typedText)`; that manager method has no return expression. The start path therefore does **not** consistently return the ID. (`index.chunk-COPWZCsC.js` bytes 27861–28569; `manager-pristine.js` bytes 896876–897180.) |
| `LocalSessions.getSession` / `getSessionList` | `getSession` delegates to manager `getSession`; the list route reaches manager `getSessionList`. The manager projects sessions through `formatSessionForEvent`, including `sessionId`, workspace and worktree fields, model, permission mode, running state, and bridge IDs. That projection does not include a Code `cliSessionId` or a complete applied rules, grants, and pending-state snapshot. (`COPWZCsC.js` bytes 37806–38158; `manager-pristine.js` bytes 1265545–1265760, 1325210–1331137, 1402448–1402797.) |
| Host `get_session` | The host tool registry calls manager session methods and presents selected task information to a Desktop-owned Code query. Its inspected output region includes the Desktop `sessionId` and selected model, directory, branch, and permission fields; it does not supply a Code ID or complete applied state. (`index.chunk-CKt-cwRV.js` bytes 209757–222747.) |

The inspected `LocalSessions` API is bound to Electron `webContents` through `setImplementation` (`index.chunk-DuaKZOPP.js` bytes 5912800–5915000). The inspected binding and host-tool registration spans contain no listener or external address. `createProxyServers` appears next to the host-tool setup (`CKt-cwRV.js` near byte 397801), but this evidence does not establish an externally callable read endpoint. Other parts of the app may have transports; this pass did not assess them.

A selected task ID could be read through these paths **inside the renderer or hosted tool context**. The inspected paths do not establish an external read-only way to invoke them. The rendered session projection does not provide the Code session ID. Desktop metadata is named by the Desktop task ID; its contents carry the Code ID needed for the later transcript/query binding. A missing Code ID is not itself a barrier to constructing the Desktop metadata filename once its other components are known. Broader sibling enumeration might discover files technically, but it exceeds the selected-file-only policy; that policy boundary should not be described as a filesystem limitation. `bridgeSessionId` is a separate field and is not evidence of the Code session ID.

### Source identity and inspection log

All four extracted files matched the published SHA-256 table:

| File | SHA-256 |
|---|---|
| `manager-pristine.js` | `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f` |
| `index.chunk-COPWZCsC.js` | `b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950` |
| `index.chunk-DuaKZOPP.js` | `f160a24940ee11cea6a788a9038e95c14fb150889977dcfa331fd9b07aba0c96` |
| `index.chunk-CKt-cwRV.js` | `dad88ac66fe13f72d0225c49d48e124d238ff643ff96426c4a2020482621e62d` |

I used `sha256sum` and static byte, token, and method-span inspection. I did not execute app modules, read task records, use live access, or write files.

The remaining evidence is a supported way to select and read one task’s Desktop and Code IDs outside the app’s private UI context, or a new selected-task receipt that supplies them, followed by live verification of the exact metadata and applied-state path.

### Coordinator correction

The returned delta conflated the Desktop metadata filename with the Code ID used for transcript/query binding. I corrected that sentence against `getSessionFilePath` at byte 919665 and its save call at byte 937636 in the same manager source: it joins the selected storage directory with the Desktop session ID plus `.json`. The original returned report remains separately hashed in the evidence manifest. This correction does not supply the missing external path to the account, organization, user-data root, or selected Desktop task identity.
