import csv
import hashlib
import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
CLAIMS = ROOT / "examples" / "claims.csv"
BAD = ROOT / "examples" / "bad_claims.csv"
PASS_FILE = ROOT / "examples" / "GATE_PASS.json"


def run(*args, cwd=ROOT):
    return subprocess.run([PY, "-m", "claim_gate", *args], cwd=str(cwd),
                         capture_output=True, text=True)


def test_offline_pass():
    if PASS_FILE.exists():
        PASS_FILE.unlink()
    r = run("check", str(CLAIMS), "--max-age-days", "3650")
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    assert PASS_FILE.exists()
    doc = json.loads(PASS_FILE.read_text())
    assert doc["rows"] == 3
    assert doc["csv_sha256"] == hashlib.sha256(CLAIMS.read_bytes()).hexdigest()
    if PASS_FILE.exists():
        PASS_FILE.unlink()


def test_bad_claims_fail():
    p = ROOT / "examples" / "GATE_PASS_bad.json"
    if p.exists():
        p.unlink()
    r = run("check", str(BAD), "--out", str(p))
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    if p.exists():
        p.unlink()


def test_verify_pass_and_invalidate(tmp_path):
    from datetime import date
    import re
    claims_copy = tmp_path / "claims.csv"
    text = CLAIMS.read_text(encoding="utf-8")
    text = re.sub(r"\d{4}-\d{2}-\d{2}", date.today().isoformat(), text)
    claims_copy.write_text(text, encoding="utf-8")
    pass_file = tmp_path / "GATE_PASS.json"
    r = run("check", str(claims_copy), "--out", str(pass_file))
    assert r.returncode == 0
    r = run("verify", str(claims_copy), "--pass-file", str(pass_file))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    # tamper
    original = claims_copy.read_text()
    claims_copy.write_text(original + "\n")
    try:
        r = run("verify", str(claims_copy), "--pass-file", str(pass_file))
        assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    finally:
        claims_copy.write_text(original)


def test_missing_column_fails():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.csv"
        p.write_text("claim,evidence_url,checked_at\na,https://example.com,x\n", encoding="utf-8")
        r = run("check", str(p))
        assert r.returncode == 1
        assert "missing required column" in r.stdout + r.stderr


def test_invalid_date_fails():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.csv"
        p.write_text("claim,evidence_url,evidence_quote,checked_at\n"
                     "c,https://example.com,q,not-a-date\n", encoding="utf-8")
        r = run("check", str(p))
        assert r.returncode == 1
        assert "not a valid ISO date" in (r.stdout + r.stderr)


def test_empty_quote_fails():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.csv"
        p.write_text("claim,evidence_url,evidence_quote,checked_at\n"
                      "c,https://example.com,," + __import__("datetime").date.today().isoformat() + "\n", encoding="utf-8")
        r = run("check", str(p))
        assert r.returncode == 1
        assert "empty" in (r.stdout + r.stderr).lower()


def test_max_age_days():
    import tempfile
    from datetime import date, timedelta
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.csv"
        old = (date.today() - timedelta(days=100)).isoformat()
        p.write_text(f"claim,evidence_url,evidence_quote,checked_at\nc,https://example.com,q,{old}\n",
                     encoding="utf-8")
        r = run("check", str(p), "--max-age-days", "30")
        assert r.returncode == 1


@pytest.mark.skipif(not os.getenv("CLAIM_GATE_LIVE"), reason="set CLAIM_GATE_LIVE=1")
def test_live_claims():
    if PASS_FILE.exists():
        PASS_FILE.unlink()
    r = run("check", str(CLAIMS), "--live", "--max-age-days", "3650")
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    if PASS_FILE.exists():
        PASS_FILE.unlink()


def test_empty_csv_fails():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "empty.csv"
        p.write_text("claim,evidence_url,evidence_quote,checked_at\n", encoding="utf-8")
        r = run("check", str(p))
        assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
        assert "no claims to check" in (r.stdout + r.stderr)


def test_renamed_columns_config():
    import json, tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cfg = td / "cfg.json"
        cfg.write_text(json.dumps({
            "required_columns": ["statement", "source_url", "excerpt", "verified_on"],
            "max_age_days": 30,
        }), encoding="utf-8")
        # valid row
        p = td / "data.csv"
        from datetime import date
        p.write_text(
            "statement,source_url,excerpt,verified_on\n"
            "c,https://example.com,q,%s\n" % date.today().isoformat(),
            encoding="utf-8",
        )
        r = run("check", str(p), "--config", str(cfg))
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
        # invalid: bad url, empty excerpt, bad date
        p2 = td / "bad.csv"
        p2.write_text(
            "statement,source_url,excerpt,verified_on\n"
            "c,not-a-url,,not-a-date\n",
            encoding="utf-8",
        )
        r2 = run("check", str(p2), "--config", str(cfg))
        assert r2.returncode == 1, (r2.returncode, r2.stdout, r2.stderr)
        out = r2.stdout + r2.stderr
        assert "http" in out.lower()
        assert "empty" in out.lower()
        assert "ISO date" in out or "iso date" in out.lower()
PY