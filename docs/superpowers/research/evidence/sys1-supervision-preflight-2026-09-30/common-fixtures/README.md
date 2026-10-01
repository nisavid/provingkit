# Supervision outcome checks

These checkers grade the synthetic parser and report artifacts in `../ordinary-workloads/`. The task instructions use ordinary language. Run `python -m unittest -v test_parser_check test_report_check` here for thirteen local checks.

The parser checker observes the program's command-line interface, including signed and blank-row handling and malformed input. Its error contract is exit 1, empty stdout, and `malformed measurement` followed by a newline on stderr. It rejects unrelated tracebacks. The parser reference and checkers remain outside evaluated projects.

The report checker accepts the selected CSV or JSON file, in input or sorted order, as the sole output-directory entry. It checks exact numeric values while accepting equivalent notation. It rejects numeric strings, duplicate keys, wrong headers, missing or reordered rows, inexact numbers, and obsolete output. The controller chooses format and order from delivered requirements, not from inferred intent. A report file alone does not establish that the agent generated it from the source rows.

These local checks establish the synthetic oracle behavior. They do not establish native agent outcomes, useful supervision, context adequacy, or general parser correctness. The preflight contract and native records govern those separate claims.
