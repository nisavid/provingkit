DONE / clean for binding `e0b2003ca5a493ab44ea3a95e8a4efaa203797eed7b9ec1dc7fe4fd51fa46286`.

Both findings are resolved. `runner.mjs:diagnostic` preserves bounded messages, codes, and two cause levels while removing the authentication value and bearer/basic values. The added synthetic checks cover connection causes, credential removal, and a failed digest invariant before dispatch.

`launch.py:supervise` records separate initialization, supervision, termination, and reconciliation intervals. The contract states that these exclude the final launcher-record write; the deadline test checks the interval sum and preserves started-unknown/unattempted accounting.

All 28 listed input hashes, canonical plan/request hashes, and the supplied binding payload match. The private packet and pinned source hashes are unchanged, so the previously verified request construction, policy projection, export disclosure, and transport constraints remain applicable.

Nine Node passes, one launcher pass, and the eight-request mock completion are coordinator-observed evidence. I read, parsed, and hashed only; I ran no source, tests, network requests, or model calls and changed no files. Execution acceptance remains pending.