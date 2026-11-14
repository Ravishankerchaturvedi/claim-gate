# claim-gate

[![tests](https://github.com/Ravishankerchaturvedi/claim-gate/actions/workflows/tests.yml/badge.svg)](https://github.com/Ravishankerchaturvedi/claim-gate/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

**Block hallucinated facts before they reach a prospect.** claim-gate fails any row in a CSV that lacks a source
URL, an exact quote and a fresh check date, and with `--live` it confirms each quote is really on the page. A pass
is bound to the file's sha256, so editing the list after the check invalidates it.

Use it for sales and marketing lists, lead research, and any AI agent or LLM pipeline that writes facts about real
companies. No dependencies; standard library only.

## Problem

Lists sent to prospects must not contain invented facts. A row added from memory passes a glance but fails a stranger. claim-gate makes a pass depend on a real URL, a real quote and a recent check date, tied to the exact file by its sha256.

## Install

```bash
pip install -e .[test]
```

## Quickstart

```bash
claim-gate check examples/claims.csv --max-age-days 3650
claim-gate verify examples/claims.csv
```

Live check (fetches each URL, one request every 2 seconds):

```bash
claim-gate check examples/claims.csv --live --max-age-days 3650
```

Real output of the quickstart above (run on 2026-10-30):

```
$ claim-gate check examples/claims.csv --max-age-days 3650
PASS -> examples/GATE_PASS.json
$ claim-gate verify examples/claims.csv
PASS: CSV matches gate pass
$ claim-gate check examples/claims.csv --live --max-age-days 3650
PASS -> examples/GATE_PASS.json
```

The example quotes were checked live on 2026-10-29; for your own lists, keep the default of 30.

A failing file looks like this:

```
$ claim-gate check examples/bad_claims.csv
row 1: evidence_url is not an http(s) URL
row 2: evidence_quote is empty
row 3: checked_at is older than 30 days
```

## How it works

Reads the CSV with `csv.DictReader`, checks required columns from config (default: claim, evidence_url, evidence_quote, checked_at), validates each row (non-empty claim, http(s) URL, non-empty quote, valid ISO date within max age), optionally fetches each URL and confirms the normalised quote appears on the page, then writes `GATE_PASS.json` with the file's sha256 and row count. `verify` re-checks the sha256 so a changed CSV invalidates the pass.

## Configuration

Required columns and max age come from a JSON config:

```bash
claim-gate check data.csv --config cfg.json --max-age-days 14
```

```json
{"required_columns": ["claim", "evidence_url", "evidence_quote", "checked_at"], "max_age_days": 30}
```

Columns may be renamed; roles are taken by position (claim, URL, quote, date).

## Use it with AI agents

Put claim-gate after any LLM step that writes claims, and before anything is sent or published:

```bash
claim-gate check leads.csv --live && claim-gate verify leads.csv && send_the_list leads.csv
```

- Exit code `0` = pass, `1` = a row failed (reasons are printed per row), `2` = bad input (for example a missing file).
- The pass file (`GATE_PASS.json`) records the CSV's sha256, the row count and the check time; `verify` refuses a
  changed file.
- The repo ships a `SKILL.md`, so coding agents that read skills (for example Claude Code) can run the gate
  themselves.

## Limits

- Offline checks validate shape and freshness only; `--live` confirms the quote appears on the page after normalising whitespace and HTML.
- No JavaScript rendering; logged-out pages only.
- One request per 2 seconds during `--live`.
- Examples in `examples/claims.csv` are real quotes verified live on 2026-10-29.

## About

Built by Ravi Shanker Chaturvedi at RAD Media, Mumbai. We use this gate on our own lead research; we build AI
systems for growing businesses. Questions, bugs or a custom build: open an issue.