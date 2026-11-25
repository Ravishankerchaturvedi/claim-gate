# Changelog

## 0.1.1 — 2026-11-25

- JSON and JSONL input: `check` now accepts a `.json` file (a top-level array of row objects, or an object holding
  that array under `rows`, `claims`, `data` or `items`) and `.jsonl`/`.ndjson` (one object per line), alongside CSV,
  chosen by file extension. A missing JSON field fails as empty; malformed JSON is bad input (exit 2); any other
  extension is rejected with exit 2.
- The gate pass records the input file's sha256 as `file_sha256` (was `csv_sha256`); the CLI positional argument is
  now `input` instead of `csv`; `verify` messages say "input file" instead of "CSV".

## 0.1.0 — 2026-10-30

Initial release.