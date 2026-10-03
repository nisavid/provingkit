Add a `--sort` option to the item report command. Support `input`, `item`, and
`total`: preserve first-seen order by default; sort by item name ascending for
`item`; and sort by total units descending, then item name ascending, for
`total`. Reject other values without replacing an existing report. Preserve
the current input, output, and error behavior otherwise.

Update the tests and README, verify the change, and commit it locally. The
agreed test boundary is the `report.py` command-line interface. Keep the local
branch and its commit; do not push, open a pull request, or clean up the project.
Use the installed authoring instructions and skills where applicable. Work only
in this disposable repository, without package installation, external services,
Jev or jev-axi calls, or live configuration changes. If needed, use at most two
native child-agent dispatches, both on GPT-6.1 Sol with high or lower effort;
do not let children delegate or invoke another harness. The existing observation
files and Git hook are experiment equipment; leave them unchanged and out of
the commit. If a required capability or permission is unavailable, report that
limitation rather than working around it.
