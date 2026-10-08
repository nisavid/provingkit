# Inventory report seed

This small Python repository reports inventory from a JSON file. It uses only the Python standard library. Run each command with the current Python executable from the repository root:

```sh
python bin/inventory-report --input fixtures/inventory.json
python bin/inventory-report --input fixtures/inventory.json --warehouse South
python bin/low-stock --input fixtures/inventory.json --threshold 2
python jobs/archive-inventory.py --input fixtures/inventory.json --output inventory-archive.tsv
```

Input is a JSON object with an `items` array. Each item has a `sku` string, a `warehouse` string, and an `on_hand` integer. The SKU and warehouse pair must be unique. SKU and warehouse must be nonempty and cannot contain tabs or line breaks. This restriction keeps tab-separated output unambiguous. `on_hand` must be nonnegative; booleans are invalid. The fixture has North and South warehouses, including a zero quantity. `fixtures/empty-inventory.json` supplies an empty inventory.

The report prints `sku`, `warehouse`, and `on_hand` as tab-separated columns with a header. Quotation marks are literal characters, not field delimiters. It prints all rows by default; `--warehouse NAME` selects one warehouse. An empty selection prints only the header. Row order is unspecified. Invalid input or arguments return a nonzero status and a diagnostic on stderr. There is no format option in this baseline CLI.

`low-stock` prints the same header and rows whose quantity is at or below `--threshold`, including zero. The threshold defaults to 2 and must be nonnegative. `archive-inventory.py` writes the complete tab-separated report to `--output`; its parent directory must exist. Both consumers call the report without a format option and use its public text output.

Run the ordinary developer checks from this directory:

```sh
python -m unittest discover -s tests -v
```
