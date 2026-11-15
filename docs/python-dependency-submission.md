# Submit the resolved Python validation inventory

The [dependency workflow](../.github/workflows/dependency-submission.yml) submits the Python packages that a fresh installation of `requirements.txt` actually resolves. The snapshot includes direct and transitive packages, exact versions, development scope, and dependency edges. Pull requests verify the converter and caller with a read-only token. Submission runs only for this repository's trusted `main` pushes or a manual invocation on `main`.

The read-only job uses Python 3.13 and the same maintained inventory as validation. A fresh virtual environment keeps runner preinstalls out of the installation report. It consumes pip's supported [version-1 installation report](https://pip.pypa.io/en/stable/reference/installation-report/); it does not introduce a lockfile or a second dependency resolver.

Immediately after resolution, that job retains only the report fields the converter consumes and captures them in a same-run job output, before tests execute installed dependency code. Later test failures still prevent the dependent submission job from running. Missing output and compact reports larger than 64 KiB stop submission. The handoff uses no artifact upload or cache. The repository-write job installs only the reviewed parser, never the project dependency inventory; project dependency code therefore runs in the read-only job.

Snapshot construction runs without `GH_TOKEN` in its step environment. Only the subsequent API preflight and submission step receives that credential. These steps share a repository-write job and runner; step separation is cooperative and does not isolate the parser from every ambient runner capability.

## Build a snapshot offline

Install the maintained requirements, then pass the report and its source identity to the converter:

```sh
python scripts/build_python_dependency_snapshot.py \
  --requirements requirements.txt --report install-report.json \
  --sha "$GITHUB_SHA" --ref refs/heads/main \
  --repository "$GITHUB_REPOSITORY" --run-id "$GITHUB_RUN_ID" \
  --output snapshot.json
```

The command reads local evidence and writes a new JSON file. It performs no installation, resolution, network request, or submission. Source arguments are declarations; the workflow separately checks the checkout and current main revision. Use a fresh output path. Existing output is preserved and returns failure.

Supported inputs are a nonempty inventory of ordinary exact pins and a complete pip version-1 report from that inventory, with its marker environment. Selected extras and direct URL dependencies are outside this initial adapter's input contract. Inactive optional registry dependencies are excluded according to the reported metadata environment. Direct URLs are refused even when their markers are inactive. Extra report keys cannot activate the unsupported plural extras or dependency-group marker contexts. The converter checks requested roots, resolved versions, active dependencies, and reachability; contradictory or incomplete evidence must fail before submission.

The requirements file is limited to 1 MiB and reports to 10 MiB. Each requirement expression is limited to 128 KiB of UTF-8 and at most 32 opening parentheses, including occurrences inside quotes. Each named environment value and reported package version is limited to 256 UTF-8 bytes. The converter checks these bounds before the corresponding requirement parsing, version parsing, or marker evaluation and refuses larger inputs. These limits bound the parser's admitted work while allowing substantial headroom over the observed CI metadata. Version clauses are tested individually against one parsed version per package so large exclusion sets do not construct quadratic combined ranges or repeatedly parse the candidate version. JSON parsing retains Python's nesting and numeric limits.

The converter emits the [GitHub dependency snapshot format](https://docs.github.com/en/rest/dependency-graph/dependency-submission), binding the commit, ref, run, stable producer correlator, and scan time. Its logical manifest is the repository's `requirements.txt`. Package identities use normalized Python names and Python package URLs. Both resolved-map keys and dependency references use those package URLs.

## Component boundary

The parser dependency is PyPA `packaging` 26.3 from PyPI, using the ordinary pure-Python wheel. It declares no runtime dependencies. The candidate's canonical source is [revision `929fd4b1`](https://github.com/pypa/packaging/tree/929fd4b1410ac7ef61ef3f45b2f5d7e87711a9b5). The published wheel's SHA-256 is `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c`; its 23 package files and three license files match that source. Preserve the upstream licensing.

The submission job requires the maintained parser pin to match the reviewed version, downloads that wheel without installing it, checks its reviewed SHA-256, then installs only that local wheel with index access and dependency acquisition disabled. A substituted parser fails before installation.

This boundary admits package-name, version, requirement, and marker parsing for this producer. It supplies no runtime downloader, remote resolver, persistent service, or additional privilege. Bind the exact pin, registry artifact, source correspondence, licensing, dependency closure, provenance evidence and its actual verification status, and the consumer checks before adoption. Retain the PyPI publisher provenance for the canonical repository; no attestation-absence exception is selected. Available provenance and a matching subject digest do not themselves establish cryptographic signature verification.

Version updates enter the existing Dependabot PR and review process. This producer selects no new autonomous-upgrade mode or maintenance service. Changed publishers, runtime acquisition, dependency closure, or required effects need renewed component assessment rather than an assumed continuation of this identity.

## Verify the consumer result

Run the owning examples with:

```sh
python -m unittest tests.test_python_dependency_submission
```

The offline examples check snapshot contents and refusals. The caller examples check declared events, permissions, source binding, and failure propagation. They do not establish hosted event behavior or GitHub's retained inventory.

Before accepting the live producer, retain its main run and submission result and retrieve the graph GitHub actually retained. Compare package names, versions, and available relationships with the fresh report and generated snapshot. A successful install, test run, or snapshot API response alone does not establish graph coverage. Preserve missing or unavailable observations explicitly. Main can advance during an API operation; the workflow's drift check and normal concurrency controls do not provide a conditional remote write.

`mergecraft:configuring-repositories` owns the repository walkthrough that consumes this evidence. The separate reusable-guidance work records general lessons without turning this repository's package or gate choices into universal defaults. Any later correction belongs in the maintained converter, workflow, and these consumer examples.
