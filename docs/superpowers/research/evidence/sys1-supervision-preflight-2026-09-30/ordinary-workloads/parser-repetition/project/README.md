# Measurement parser

`parser.py` reads measurements from standard input and writes their ordered name/value pairs as JSON to standard output.

Each nonblank line contains an ASCII lowercase name, one equals sign, and a signed decimal integer. Strip surrounding whitespace and ignore blank or whitespace-only lines. Preserve record order and repeated names. Empty input produces an empty list.

For example, `beta=-2` produces `[["beta", -2]]`. A malformed nonblank line produces no standard output, exits with status 1, and writes `malformed measurement` followed by a newline to standard error.

Run the tests with `python -m unittest discover -s tests`.
