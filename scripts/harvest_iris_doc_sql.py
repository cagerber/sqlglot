#!/usr/bin/env python3
"""Harvest InterSystems IRIS SQL Reference examples into iris_doc_sql fixtures.

Usage (from sqlglot repo root):
  uv run python scripts/harvest_iris_doc_sql.py RSQL_substring RSQL_replace
  uv run python scripts/harvest_iris_doc_sql.py --all-pending
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from html import unescape
from pathlib import Path

from sqlglot import parse_one

BASE_URL = "https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY="
FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests/dialects/fixtures/iris_doc_sql"
MANIFEST_PATH = FIXTURE_DIR / "_manifest.json"

SKIP_PATTERNS = (
    "SET q",
    "&sql(",
    "##class",
    "WRITE ",
    "DO rset",
    "IF qStatus",
    "SET student",
    "SET clearit",
    "SET myquery",
    "SET studentupdate",
)


def fetch(key: str) -> str:
    req = urllib.request.Request(BASE_URL + key, headers={"User-Agent": "ods-harvest"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_title(html: str, key: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    if m:
        return unescape(m.group(1)).strip()
    return key.replace("_", " ")


def is_synopsis(stmt: str) -> bool:
    if "..." in stmt:
        return True
    if re.search(
        r"\{,|\[%keyword\]|scalar-expression|value-assignment|selectItem|tablename\b",
        stmt,
        re.I,
    ):
        return True
    if re.search(r"\b(table|column2|value2)\b", stmt, re.I) and not re.search(
        r"Sample\.|SQLUser\.|MyTable|Employees|MyStudents",
        stmt,
    ):
        return True
    return False


def slug(sql: str, index: int) -> str:
    digest = hashlib.md5(sql.encode()).hexdigest()[:8]
    return f"ex_{index:03d}_{digest}"


def harvest_stmts(html: str) -> list[str]:
    pres = re.findall(r"<pre[^>]*>(.*?)</pre>", html, re.I | re.S)
    seen: set[str] = set()
    out: list[str] = []
    for block in pres:
        text = unescape(re.sub(r"<[^>]+>", "", block)).strip()
        if any(pat in text for pat in SKIP_PATTERNS):
            continue
        if re.match(
            r"(?i)^\s*(SELECT|INSERT|UPDATE|DELETE|TRUNCATE|WITH|CREATE|ALTER)\b",
            text,
        ):
            stmt = re.sub(r"\s+", " ", text).strip().rstrip(";")
            if len(stmt) < 10 or stmt in seen:
                continue
            seen.add(stmt)
            out.append(stmt)
            continue
        if re.match(r"(?i)^\s*FROM\b", text):
            stmt = re.sub(r"\s+", " ", f"SELECT * {text.strip()}").strip().rstrip(";")
            if len(stmt) >= 10 and stmt not in seen:
                seen.add(stmt)
                out.append(stmt)
            continue
        parts = [text] if "\n" not in text else re.split(r"\n(?=[A-Z])", text)
        for part in parts:
            stmt = re.sub(r"\s+", " ", part).strip().rstrip(";")
            if not stmt or stmt in seen:
                continue
            if not re.match(
                r"(?i)^(SELECT|INSERT|UPDATE|DELETE|TRUNCATE|WITH|CREATE|ALTER)\b",
                stmt,
            ):
                continue
            if len(stmt) < 10:
                continue
            seen.add(stmt)
            out.append(stmt)
    return out


def build_examples(stmts: list[str], *, max_parseable: int = 30, max_skipped: int = 8) -> list[dict]:
    examples: list[dict] = []
    for index, stmt in enumerate(stmts, start=1):
        ex: dict = {
            "id": slug(stmt, index),
            "section": "Examples",
            "sql": stmt,
            "roundtrip": False,
        }
        if is_synopsis(stmt):
            ex["skip_parse"] = True
            ex["skip_reason"] = "doc synopsis placeholder, not runnable SQL"
        else:
            try:
                parse_one(stmt, read="iris")
            except Exception as exc:
                ex["skip_parse"] = True
                ex["skip_reason"] = str(exc)[:200]
        examples.append(ex)

    parseable = [e for e in examples if not e.get("skip_parse")]
    skipped = [e for e in examples if e.get("skip_parse")]
    if len(parseable) > max_parseable:
        parseable = parseable[:max_parseable]
    if len(skipped) > max_skipped:
        skipped = skipped[:max_skipped]
    return parseable + skipped


def write_fixture(key: str, title: str | None = None) -> dict:
    html = fetch(key)
    title = title or extract_title(html, key)
    stmts = harvest_stmts(html)
    examples = build_examples(stmts)
    payload = {
        "doc_key": key,
        "doc_url": BASE_URL + key,
        "title": title,
        "doc_version": "2026.1",
        "examples": examples,
    }
    path = FIXTURE_DIR / f"{key}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    ok = sum(1 for e in examples if not e.get("skip_parse"))
    sk = sum(1 for e in examples if e.get("skip_parse"))
    return {"doc_key": key, "path": str(path), "parseable": ok, "skipped": sk, "total": len(examples)}


def pending_keys() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    keys: list[str] = []
    for section in ("pages", "string_functions", "clause_pages", "dml_commands", "index_pages", "predicate_pages", "aggregate_pages", "window_pages", "function_pages", "unary_pages", "optimization_pages", "datatype_pages", "gsql_pages"):
        for entry in manifest.get(section, []):
            if entry.get("status") == "pending" and entry.get("doc_key"):
                keys.append(entry["doc_key"])
    return keys


def update_manifest_harvested(key: str) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for section in ("pages", "string_functions", "clause_pages", "dml_commands", "index_pages", "predicate_pages", "aggregate_pages", "window_pages", "function_pages", "unary_pages", "optimization_pages", "datatype_pages", "gsql_pages"):
        for entry in manifest.get(section, []):
            if entry.get("doc_key") == key:
                entry["status"] = "harvested"
                entry["fixture"] = f"{key}.json"
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keys", nargs="*", help="RSQL doc keys to harvest")
    parser.add_argument("--all-pending", action="store_true")
    args = parser.parse_args()
    keys = pending_keys() if args.all_pending else args.keys
    if not keys:
        parser.error("provide doc keys or --all-pending")
    for key in keys:
        result = write_fixture(key)
        update_manifest_harvested(key)
        print(
            f"{result['doc_key']}: {result['parseable']} parseable, "
            f"{result['skipped']} skipped, {result['total']} total -> {result['path']}"
        )


if __name__ == "__main__":
    main()
