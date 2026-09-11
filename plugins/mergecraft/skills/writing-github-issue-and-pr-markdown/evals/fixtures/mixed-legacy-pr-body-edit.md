# Mixed legacy pull-request body edit

Field: Pull-request body.

The exact current body is shown as a JSON string so every newline byte is visible:

````json
"Legacy opening wraps at an old width\r\nand this retained continuation stays.\r\n\r\n<!-- keep:opaque -->\nReplace this placeholder.\n\n```text\r\nopaque payload\r\n```\r\n"
````

Replace only the UTF-8 bytes `Replace this placeholder.` with one newly authored paragraph: explain that retry reconciliation now stops when object identity is ambiguous and requires an operator to reconcile the same intent before another write. Retain every other byte exactly, including the legacy wrap, mixed CRLF and LF sequences, control marker, fenced payload, and terminal CRLF.

Do not repair other content or update the pull request.
