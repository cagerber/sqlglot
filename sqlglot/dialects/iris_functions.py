"""
InterSystems IRIS SQL function / operator metadata for the Trifour dialect fork.

Used by the parser (pseudo-field allowlist) and by downstream lineage tooling
(arity hints, argument roles). Doc examples live in
``tests/dialects/fixtures/iris_doc_sql/`` with ``doc_url`` on each row.

Completeness checks: compare fixture ``doc_key`` sets to pages listed in
``docs/syntax/sql/sql4.md`` (ODS repo) and InterSystems RSQL_* doc pages.
"""

from __future__ import annotations

from typing import Any

# ``SELECT %ID`` / ``%%TABLENAME`` — not ``%SQLUPPER(...)`` or ``%Dictionary.*``.
IRIS_PSEUDO_FIELD_NAMES = frozenset({"ID", "TABLENAME", "CLASSNAME"})

# ``%NAME(...)`` SQL functions (case-insensitive); stored in AST as ``Anonymous``.
IRIS_PERCENT_SQL_FUNCTIONS = frozenset(
    {
        "EXTERNAL",
        "SQLUPPER",
        "SQLSTRING",
        "EXACT",
        "ODBCOUT",
    }
)

# ``column %OP expr`` — not pseudo-fields.
IRIS_PERCENT_PREDICATES = frozenset(
    {"STARTSWITH", "PATTERN", "FIND", "INSET", "INLIST", "MATCHES"}
)

# Query optimizer hints (GSOC_hints) — position-specific; not predicates or pseudo-fields.
IRIS_SELECT_OPTIMIZATION_HINTS = frozenset({"DORUNTIME", "NORUNTIME"})

IRIS_FROM_OPTIMIZATION_HINTS = frozenset(
    {
        "FIRSTTABLE",
        "INORDER",
        "NOFIXEDSTATS",
        "NOFPLAN",
        "PARALLEL",
        "NOPARALLEL",
        # Advanced (documented on GSOC_hints; parse-only for lineage fixtures).
        "ALLINDEX",
        "NOFLATTEN",
        "NOTOPOPT",
    }
)

IRIS_WHERE_OPTIMIZATION_HINTS = frozenset({"NOINDEX"})

IRIS_OPTIMIZATION_HINTS = (
    IRIS_SELECT_OPTIMIZATION_HINTS
    | IRIS_FROM_OPTIMIZATION_HINTS
    | IRIS_WHERE_OPTIMIZATION_HINTS
)


def _spec(
    name: str,
    *,
    min_args: int | None = None,
    max_args: int | None = None,
    variadic: bool = False,
    lineage_role: str = "expression",
) -> dict[str, Any]:
    return {
        "name": name,
        "min_args": min_args,
        "max_args": max_args,
        "variadic": variadic,
        "lineage_role": lineage_role,
    }


# Lineage-oriented registry: name → arity / role (extend per harvested doc page).
IRIS_FUNCTION_LINEAGE: dict[str, dict[str, Any]] = {
    "CONCAT": _spec("CONCAT", min_args=2, max_args=2, lineage_role="string_concat"),
    "STRING": _spec("STRING", variadic=True, min_args=1, lineage_role="string_concat"),
    "SUBSTRING": _spec("SUBSTRING", min_args=2, max_args=3, lineage_role="substring"),
    "SUBSTR": _spec("SUBSTR", min_args=2, max_args=3, lineage_role="substring"),
    "REPLACE": _spec("REPLACE", min_args=3, max_args=3, lineage_role="replace"),
    "TRIM": _spec("TRIM", min_args=1, max_args=3, lineage_role="trim"),
    "LTRIM": _spec("LTRIM", min_args=1, max_args=1, lineage_role="trim"),
    "RTRIM": _spec("RTRIM", min_args=1, max_args=1, lineage_role="trim"),
    "POSITION": _spec("POSITION", min_args=2, max_args=2, lineage_role="position"),
    "CHARINDEX": _spec("CHARINDEX", min_args=2, max_args=3, lineage_role="position"),
    "INSTR": _spec("INSTR", min_args=2, max_args=4, lineage_role="position"),
    "LENGTH": _spec("LENGTH", min_args=1, max_args=1, lineage_role="length"),
    "CHAR_LENGTH": _spec("CHAR_LENGTH", min_args=1, max_args=1, lineage_role="length"),
    "CHARACTER_LENGTH": _spec("CHARACTER_LENGTH", min_args=1, max_args=1, lineage_role="length"),
    "STUFF": _spec("STUFF", min_args=4, max_args=4, lineage_role="replace"),
    "NOW": _spec("NOW", min_args=0, max_args=0, lineage_role="current_time"),
    "NVL": _spec("NVL", min_args=2, max_args=2, lineage_role="coalesce"),
    "COALESCE": _spec("COALESCE", variadic=True, min_args=2, lineage_role="coalesce"),
    "DATEADD": _spec("DATEADD", min_args=3, max_args=3, lineage_role="date_add"),
    "LAST_DAY": _spec("LAST_DAY", min_args=1, max_args=1, lineage_role="date"),
    "$EXTRACT": _spec("$EXTRACT", min_args=2, max_args=3, lineage_role="substring"),
    "$PIECE": _spec("$PIECE", min_args=2, max_args=4, lineage_role="substring"),
    "$LENGTH": _spec("$LENGTH", min_args=1, max_args=2, lineage_role="length"),
    "$FIND": _spec("$FIND", min_args=2, max_args=3, lineage_role="position"),
    "%SQLUPPER": _spec("%SQLUPPER", min_args=1, max_args=1, lineage_role="collation"),
    "%EXTERNAL": _spec("%EXTERNAL", min_args=1, max_args=1, lineage_role="format"),
    "%STARTSWITH": _spec("%STARTSWITH", min_args=2, max_args=2, lineage_role="predicate"),
    "%PATTERN": _spec("%PATTERN", min_args=2, max_args=2, lineage_role="predicate"),
    "%FIND": _spec("%FIND", min_args=2, max_args=2, lineage_role="predicate"),
    "%INSET": _spec("%INSET", min_args=2, max_args=2, lineage_role="predicate"),
    "%INLIST": _spec("%INLIST", min_args=2, max_args=3, lineage_role="predicate"),
    "%MATCHES": _spec("%MATCHES", min_args=2, max_args=2, lineage_role="predicate"),
    "FOR SOME %ELEMENT": _spec(
        "FOR SOME %ELEMENT", min_args=2, max_args=3, lineage_role="predicate"
    ),
}


def lineage_spec_for_expression_name(name: str) -> dict[str, Any] | None:
    key = (name or "").upper()
    if key.startswith("%"):
        key = key.upper()
    return IRIS_FUNCTION_LINEAGE.get(key)
