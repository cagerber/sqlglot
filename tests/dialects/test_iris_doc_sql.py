"""Parse harvested InterSystems IRIS SQL Reference examples (read=iris).

Fixture files live under ``fixtures/iris_doc_sql/*.json``. Each example carries
``doc_url`` / ``doc_key`` for completeness checks against sql4.md page lists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sqlglot import parse_one

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "iris_doc_sql"


def _iter_doc_examples():
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        doc_key = payload["doc_key"]
        doc_url = payload["doc_url"]
        for example in payload.get("examples", []):
            yield pytest.param(
                doc_key,
                doc_url,
                example,
                id=f"{doc_key}:{example['id']}",
            )


@pytest.mark.parametrize("doc_key,doc_url,example", list(_iter_doc_examples()))
def test_harvested_doc_sql_parses(doc_key: str, doc_url: str, example: dict) -> None:
    if example.get("skip_parse"):
        pytest.skip(example.get("skip_reason", "skip_parse"))
    sql = example["sql"]
    tree = parse_one(sql, read="iris")
    assert tree is not None, f"parse failed for {doc_key} ({doc_url})"
    if example.get("roundtrip"):
        assert sql == tree.sql(dialect="iris"), (
            f"roundtrip mismatch for {doc_key} ({doc_url}) example {example['id']}"
        )


def test_doc_fixture_index_has_urls() -> None:
    """Every fixture file must declare doc_key and doc_url for completeness tooling."""
    paths = list(FIXTURE_DIR.glob("*.json"))
    assert paths, f"no fixtures under {FIXTURE_DIR}"
    for path in paths:
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("doc_key"), path
        assert data.get("doc_url", "").startswith("https://docs.intersystems.com/"), path
        assert data.get("examples"), f"{path.name}: no examples harvested yet"


def test_dml_commands_manifest_harvested() -> None:
    """Every DML command listed under RSQL_COMMANDS must have a non-empty fixture."""
    manifest_path = FIXTURE_DIR / "_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("dml_commands", []):
        _assert_harvested_entry(entry)


def test_string_functions_manifest_harvested() -> None:
    """Legacy alias: string functions live under function_pages."""
    test_function_pages_manifest_harvested()


def test_function_pages_manifest_harvested() -> None:
    """Every scalar function page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("function_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def test_predicate_pages_manifest_harvested() -> None:
    """Every predicate page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("predicate_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def test_aggregate_pages_manifest_harvested() -> None:
    """Every aggregate page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("aggregate_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def test_window_pages_manifest_harvested() -> None:
    """Every window function page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("window_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def test_unary_pages_manifest_harvested() -> None:
    """Every unary operator page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("unary_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def test_optimization_pages_manifest_harvested() -> None:
    """Every optimization-hint page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("optimization_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def test_datatype_pages_manifest_harvested() -> None:
    """Every datatype page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("datatype_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def test_clause_pages_manifest_harvested() -> None:
    """Every SQL clause page marked harvested in the manifest must parse."""
    manifest = json.loads((FIXTURE_DIR / "_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("clause_pages", []):
        if entry.get("status") != "harvested":
            continue
        _assert_harvested_entry(entry)


def _assert_harvested_entry(entry: dict) -> None:
    doc_key = entry["doc_key"]
    fixture_name = entry.get("fixture")
    assert entry.get("status") == "harvested", doc_key
    assert fixture_name, doc_key
    fixture_path = FIXTURE_DIR / fixture_name
    assert fixture_path.is_file(), fixture_path
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert data["doc_key"] == doc_key
    assert data.get("examples"), doc_key
    parseable = [e for e in data["examples"] if not e.get("skip_parse")]
    assert parseable, f"{doc_key}: no parseable examples (only synopsis/skips)"
