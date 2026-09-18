# A production file-decision boundary

The prototype lets a caller ask whether original file bytes contain a historical
identity in their repository-relative path context. The repository scanner uses
the same callable as the ordinary example tests. Its purpose is to test whether
that responsibility supports useful, inexpensive tests before choosing a final
interface or migrating existing coverage.

The question is tracked in [the prototype ticket](https://github.com/nisavid/provingkit/issues/128).
The [accepted coverage map](https://github.com/nisavid/provingkit/blob/1494a78f2025544db0511c2909344973331d07e7/docs/superpowers/research/2026-09-18-file-identity-coverage.md)
and [case inventory](https://github.com/nisavid/provingkit/blob/1494a78f2025544db0511c2909344973331d07e7/docs/superpowers/research/2026-09-18-file-identity-cases.json)
describe the retained integration coverage at base
`ad31344cdcb9891438cf1e92c27c776945bee6ab`.

## Responsibility

`contains_historical_identity(relative_path: Path, original_content: bytes) -> bool`
in `scripts/validate_provingkit.py` owns the ordered composition of path-specific
transformation, format/frontmatter extraction, normalization, and identity
detection. `True` means an identity was detected; repository allowance is decided
elsewhere. Existing `ValidationError` failures propagate. Supported inputs are the
relative paths and original bytes already supplied by the repository scanner;
the prototype adds no input coercion or new path validation.

The implementation stays in the validator file. Existing tests include two
methods that copy that file into a temporary standalone script. Moving its
helpers to a module would introduce an import contract and fixture changes that
this experiment does not need. All existing helpers and tests remain intact.

The interface hides a composed decision despite its short body. It offers one
place for production and direct examples to ask that question. It does not
improve physical locality: the helpers already live together. With one production
caller, the main prospective benefit is cheaper, behavior-focused tests.

## Retained integration obligations

| Responsibility | Owner in the prototype |
| --- | --- |
| Sorted discovery, excluded directories, file reads, and symlink rejection | `_validate_historical_identities` |
| Allowlist shape, sorted entries, membership, and completeness | `_validate_historical_identities` |
| Original bytes stored for detected files and hashed against allowed entries | `_validate_historical_identities` |
| Ordered per-file transformation, format extraction, normalization, and detection | `contains_historical_identity` using existing helpers |
| Invocation order and top-level error handling | Existing `main` |
| Existing repository, CLI, encoding, path, and allowlist examples | Unchanged `tests/test_validate_provingkit.py` |

For example, BOM-frontmatter bytes pass unchanged into the predicate. The
repository scanner still records the original `content` and hashes it later;
normalized content is never substituted for those stored bytes.

## Reproduce the bounded observation

Use a clean checkout of the prototype branch with the retained history refs
required by the original test suite. Use the validation dependencies named in
`.github/workflows/provingkit-source.yml`.

```sh
python -m unittest -v tests.test_file_identity_prototype
python -m scripts.prototype_file_identity > /tmp/file-identity-prototype.json
git diff --check
```

The runner uses six ordinary examples: plain content, YAML metadata, BOM
frontmatter, the actual `CONTEXT.md` at its exact path, a reported YAML parse
error, and an accepted literal escape. It imports the unchanged suite's fixture
setup helper, creates a separate repository fixture for each case, and supplies
identical original bytes to the direct call and real validator CLI. It verifies
the direct result and the corresponding CLI result, recording setup separately.

Each direct timing is a median of five warm in-process batches of 100 calls.
Each CLI timing is one untraced subprocess, including startup and the validator
work reached for that case. A rejected fixture may stop before later checks.
These different scopes explain the cost comparison; it is not a before/after
optimization benchmark. The runner records every sample, input digest, source
commit, source-file digest, Python version, and parser dependency version.

A separate profiled CLI run observes the repository scanner calling the proposed
predicate with the original BOM-frontmatter bytes. It neither replaces nor mocks
the predicate and contributes no timing sample. This trace establishes production
reachability and the passed bytes, not allowlist-equivalence qualification.

The observations cover these examples only. They do not run the complete original
suite, qualify adversarial or allowlist equivalence, approve test migration or
removal, establish a final interface, or demonstrate hosted CI savings. The
throwaway branch is a review artifact; production implementation and the hosted
scheduling experiment remain separate decisions.
