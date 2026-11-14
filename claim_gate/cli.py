import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

from . import core
from . import fetch


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def do_check(args):
    csv_path = Path(args.csv).resolve()
    if not csv_path.is_file():
        print(f"file not found: {csv_path}", file=sys.stderr)
        return 2
    config = core.load_config(args.config) if args.config else {}
    required = config.get("required_columns", ["claim", "evidence_url", "evidence_quote", "checked_at"])
    max_age = args.max_age_days
    if max_age is None:
        max_age = config.get("max_age_days", 30)

    headers, rows = read_csv(csv_path)

    # header check
    failures = []
    for col in required:
        if col not in headers:
            failures.append((0, f"missing required column: {col}"))
    if failures:
        for rownum, reason in failures:
            print(f"row {rownum or '-'}: {reason}")
        return 1

    if not rows:
        print("no claims to check")
        return 1

    # basic validation
    failures = core.validate_rows(rows, required, max_age)

    # live checks
    if args.live and not failures:
        # only run if no basic failures? We'll still run per row that has valid URL
        pass
    url_col = required[1] if isinstance(required, list) and len(required) > 1 else "evidence_url"
    quote_col = required[2] if isinstance(required, list) and len(required) > 2 else "evidence_quote"
    if args.live:
        last = 0.0
        live_failures = []
        # map row index to row
        for idx, row in enumerate(rows, 1):
            # skip rows already failed basic? We'll still fetch if URL valid
            url = (row.get(url_col) or "").strip()
            quote = (row.get(quote_col) or "").strip()
            if not core.is_http_url(url):
                continue
            # politeness
            now = time.time()
            wait = 2.0 - (now - last)
            if wait > 0:
                time.sleep(wait)
            last = time.time()
            try:
                page, status = fetch.fetch_text(url)
            except Exception as e:
                live_failures.append((idx, f"live check: could not fetch URL ({e})"))
                continue
            if status != 200:
                live_failures.append((idx, f"live check: URL returned HTTP {status}"))
                continue
            norm_page = fetch.normalize(page)
            norm_q = fetch.normalize_quote(quote)
            if norm_q and norm_q not in norm_page:
                live_failures.append((idx, "live check: quote not found on page"))
        # merge
        failures = failures + live_failures

    # print
    for rownum, reason in failures:
        print(f"row {rownum}: {reason}")

    if failures:
        return 1

    # write pass
    if args.out:
        out_path = Path(args.out).resolve()
        display_out = args.out
    else:
        out_path = csv_path.parent / "GATE_PASS.json"
        display_out = str(Path(args.csv).parent / "GATE_PASS.json")
        if display_out in (".", ""):
            display_out = "GATE_PASS.json"
    core.write_pass(out_path, csv_path, len(rows))
    print(f"PASS -> {display_out}")
    return 0


def do_verify(args):
    csv_path = Path(args.csv).resolve()
    if not csv_path.is_file():
        print(f"file not found: {csv_path}", file=sys.stderr)
        return 2
    pass_path = Path(args.pass_file).resolve() if args.pass_file else csv_path.parent / "GATE_PASS.json"
    if not pass_path.is_file():
        print(f"no GATE_PASS.json found at {pass_path}", file=sys.stderr)
        return 1
    with open(pass_path, encoding="utf-8") as f:
        doc = json.load(f)
    current = core.file_sha256(csv_path)
    if doc.get("csv_sha256") != current:
        print("FAIL: CSV has changed since gate pass", file=sys.stderr)
        return 1
    print("PASS: CSV matches gate pass")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="claim-gate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check")
    p_check.add_argument("csv")
    p_check.add_argument("--config", default=None)
    p_check.add_argument("--live", action="store_true")
    p_check.add_argument("--max-age-days", type=int, default=None)
    p_check.add_argument("--out", default=None)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("csv")
    p_verify.add_argument("--pass-file", default=None)
    args = parser.parse_args(argv)
    if args.cmd == "check":
        rc = do_check(args)
    else:
        rc = do_verify(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()