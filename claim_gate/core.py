import csv
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone

DEFAULT_REQUIRED = ["claim", "evidence_url", "evidence_quote", "checked_at"]
DEFAULT_MAX_AGE = 30


def load_config(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_iso_date(value):
    v = (value or "").strip()
    if not v:
        return None
    v2 = v.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v2)
    except ValueError:
        # allow date-only already handled; try date
        try:
            dt = datetime.combine(date.fromisoformat(v), datetime.min.time())
        except ValueError:
            return None
    return dt.date() if isinstance(dt, datetime) else dt


def is_http_url(value):
    v = (value or "").strip()
    if not v:
        return False
    # basic parse without importing urllib for validation
    low = v.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        return False
    # must have a host after scheme
    rest = v.split("://", 1)[1]
    if not rest or rest.startswith("/"):
        return False
    host = rest.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if not host:
        return False
    return True


def _role_columns(required):
    """Map semantic roles to column names.

    By default the four required columns are, in order: claim, evidence URL,
    evidence quote, checked_at. A config may rename them; position keeps the role.
    """
    r = list(required or [])
    roles = {}
    if len(r) >= 1:
        roles["claim"] = r[0]
    if len(r) >= 2:
        roles["url"] = r[1]
    if len(r) >= 3:
        roles["quote"] = r[2]
    if len(r) >= 4:
        roles["date"] = r[3]
    return roles


def validate_rows(rows, required, max_age_days, live=False, fetcher=None):
    """Return list of (rownum, reason) failures."""
    failures = []
    today = date.today()
    cutoff = today - timedelta(days=max_age_days)
    roles = _role_columns(required)
    claim_col = roles.get("claim")
    url_col = roles.get("url")
    quote_col = roles.get("quote")
    date_col = roles.get("date")
    handled = {c for c in (claim_col, url_col, quote_col, date_col) if c}

    for idx, row in enumerate(rows, 1):
        # generic non-empty check for any required column without a known role
        for col in required or []:
            if col in handled:
                continue
            val = str(row.get(col) or "").strip() if isinstance(row, dict) else ""
            if not val:
                failures.append((idx, "%s is empty" % col))

        # a missing field (JSON rows) counts as empty, like a blank CSV cell
        if claim_col and isinstance(row, dict):
            claim = str(row.get(claim_col) or "").strip()
            if not claim:
                failures.append((idx, "%s is empty" % claim_col))

        if url_col and isinstance(row, dict):
            url = str(row.get(url_col) or "").strip()
            if not url:
                failures.append((idx, "%s is empty" % url_col))
            elif not is_http_url(url):
                failures.append((idx, "%s is not an http(s) URL" % url_col))

        if quote_col and isinstance(row, dict):
            quote = str(row.get(quote_col) or "").strip()
            if not quote:
                failures.append((idx, "%s is empty" % quote_col))

        if date_col and isinstance(row, dict):
            checked_raw = str(row.get(date_col) or "").strip()
            if not checked_raw:
                failures.append((idx, "%s is empty" % date_col))
            else:
                d = parse_iso_date(checked_raw)
                if d is None:
                    failures.append((idx, "%s is not a valid ISO date" % date_col))
                elif d < cutoff:
                    failures.append((idx, "%s is older than %d days" % (date_col, max_age_days)))
                elif d > today + timedelta(days=1):
                    failures.append((idx, "%s is in the future" % date_col))

    return failures


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_pass(path, input_path, rows):
    doc = {
        "file_sha256": file_sha256(input_path),
        "rows": rows,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return doc
