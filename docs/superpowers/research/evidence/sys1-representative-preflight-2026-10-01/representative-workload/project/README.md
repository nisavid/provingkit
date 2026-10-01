# Item report

Generate a CSV report of total units by item with Python's standard library.

## Run

From the application directory:

```sh
python report.py
```

The command reads `data/source.csv` and writes `output/report.csv`. Both paths are resolved relative to the application, so invoking `report.py` from another working directory produces the same report in the application's output directory. The output directory is created when needed.

The input has `item`, `category`, `units`, and `multiplier` columns. Each row contributes `units * multiplier` to its item's total. Numeric fields are integers. Repeated items are combined, and rows in the report preserve the order in which items first appear. The output header is `item,total_units`.

The supplied source produces:

```csv
item,total_units
bravo,20
alpha,4
charlie,11
delta,4
echo,9
```

`data/returns.csv` is a separate available dataset; the command reads only `data/source.csv`.

Successful generation is quiet and replaces the report. An input error is reported on stderr with a nonzero exit status before an existing report is replaced.

## Test

```sh
make test
```

Or run `python -m unittest discover -s tests -v`. Tests exercise the command in temporary application copies and leave generated reports outside the source tree.
