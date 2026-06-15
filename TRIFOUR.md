# Trifour fork delta (sqlglot)

Upstream: [tobymao/sqlglot](https://github.com/tobymao/sqlglot) (`v30.11.0` baseline).

ODS consumes this fork via `[tool.uv.sources] sqlglot` (editable `../3rdparty/sqlglot` in dev; git `rev` pin in CI).

## Changes in `30.11.0+trifour.18`

- **RSQL misc pages** — harvested + curated 9 remaining RSQL reference pages: RSQL_SYMBOL_TABLE, RSQL_REFMATERIAL, RSQL_dateconstruct, RSQL_defaultusernamepassword, RSQL_sqlcode, RSQL_fieldconstraint, RSQL_reservedwords, RSQL_cosvariables (2 auto-harvested), RSQL_COMMANDS (index fixture with child_doc_keys for 6 DML pages).
- **Manifest** — seeded `pages` section with 8 new RSQL entries; RSQL_COMMANDS now `page_kind: index`.

## Changes in `30.11.0+trifour.17`

- **GSQL doc harvest batch** — harvested **22** GSQL reference pages; curated fixtures for 6 pages with no DocBook `<pre>` SQL (GSQL_intr, GSQL_basics, GSQL_identifiers, GSQL_options, GSQL_rls, GSQL_impexp).
- **GSQL fixtures** — runnable examples from GSQL_langelements (13), GSQL_implicitjoins (12), GSQL_tables (12), GSQL_views (10), GSQL_collation (8), GSQL_queries (9), GSQL_procedures (6), GSQL_blobs (9), GSQL_vecsearch (4), GSQL_foreigntables (5), GSQL_foreignkeys (2), GSQL_triggers (1), GSQL_modify (4), GSQL_partitioned (2), GSQL_privileges (1), GSQL_import (1).
- **Known parser gaps** — `CREATE FOREIGN SERVER`, `CREATE FOREIGN TABLE`, `CREATE QUERY` parse as `Command` nodes (not skipped since they don't raise; tracked for future DDL parser work).

## Changes in `30.11.0+trifour.16`

- **GSQL doc harvest** — seeded `gsql_pages` manifest section with all **23** GSQL reference pages (GSQL_overview through GSQL_impexp); index fixture `GSQL_overview.json` with `child_doc_keys` + curated smoke `SELECT` exercising arrow syntax and `%ID` pseudo-field.
- **Parser** — fixed `_parse_id_var` to return `IrisPercentField` for `%ID` pseudo-fields in dotted references (`p.%ID`) instead of dropping the field name; fixed `_parse_column_ops` DOT handler to fall through to `Dot` when the right-hand-side is not a plain `Column`/`Identifier`.
- **Harvest CLI** — `pending_keys()` and `update_manifest_harvested()` now scan `gsql_pages` section.

## Changes in `30.11.0+trifour.15`

- **SQL clauses** (`RSQL_CLAUSES`): harvested all **16** child clause pages from [RSQL_CLAUSES](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_CLAUSES); index fixture `RSQL_CLAUSES.json` with `child_doc_keys` + smoke `SELECT`.
- **Parser** — `IrisCurrentOf` for embedded SQL `WHERE CURRENT OF cursor` on `UPDATE`/`DELETE`.
- **Curated fixtures** — `RSQL_into` (host-variable `SELECT … INTO :var`) and `RSQL_wherecurrentof` where DocBook has embedded-SQL examples only.
- **Manifest / tests** — `clause_pages` all `harvested`; `test_clause_pages_manifest_harvested`.
- **LONGVARCHAR** — Iris tokenizer no longer aliases `LONGVARCHAR` → `TEXT`; parses as `USER-DEFINED` / `kind=LONGVARCHAR` and round-trips on generate (distinct from `VARCHAR(MAX)`).

## Changes in `30.11.0+trifour.14`

- **SQL data types** (`RSQL_datatype`): IRIS class-style DDL (`%String(MAXLEN=30)`, `%Library.Date(MINVAL=…)`), named type parameters (`TIMESTAMP(MINVAL=…)`, UDT `Package.Class(MAXLEN=…)`), empty-string `VARCHAR('')` / `VARBINARY('')`; curated `RSQL_datatype.json` fixture (CREATE TABLE + CAST); manifest `datatype_pages`.

## Changes in `30.11.0+trifour.13`

- **Query optimization hints** (`GSOC_hints`): `IrisOptimizationHint` / `IrisOptimizedExpression` for `%DORUNTIME`, `%NORUNTIME` (SELECT), `%FIRSTTABLE`, `%INORDER`, `%NOFIXEDSTATS`, `%NOFPLAN`, `%PARALLEL`, `%NOPARALLEL` (FROM), `%NOINDEX` (WHERE); curated `GSOC_hints.json` fixture; harvest wraps bare `FROM` fragments as `SELECT * FROM …`.

## Changes in `30.11.0+trifour.12`

- **Unary operator doc fixtures** — harvested [RSQL_UNARY_OPERATORS](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_UNARY_OPERATORS): index + `RSQL_negative`, `RSQL_not`, `RSQL_positive`.
- **Manifest** — `unary_pages` section; `test_unary_pages_manifest_harvested`. Doc-harvested `-` example; curated `NOT` / unary `+` where DocBook has synopsis only.

## Changes in `30.11.0+trifour.11`

- **Scalar function doc fixtures** — harvested all **150** child pages from [RSQL_FUNCTIONS](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_FUNCTIONS); consolidated manifest section `function_pages` (replaces `string_functions`).
- **Index fixture** — `RSQL_FUNCTIONS.json` with `child_doc_keys` + cross-function smoke `SELECT`.
- **Curated synopsis** — 11 pages with no runnable doc `<pre>` SQL (e.g. `DATABASE`, `DATALENGTH`, `DAY`, `SYSDATE`) get curated `SELECT` examples aligned with DocBook signatures.
- **Parser** — `DATABASE()` and `{fn DATABASE()}` via `FUNC_TOKENS` + `FUNCTIONS` on `IrisParser`.
- **Tests** — `test_function_pages_manifest_harvested` ( `test_string_functions_manifest_harvested` delegates here).

## Changes in `30.11.0+trifour.10`

- **Window function doc fixtures** — harvested [RSQL_WINDOW_FUNCTIONS](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_WINDOW_FUNCTIONS) child pages: `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `PERCENT_RANK`, `CUME_DIST`, `NTILE`, `LAG`/`LEAD`, `FIRST_VALUE`/`LAST_VALUE`, `NTH_VALUE`, and windowed `AVG`/`COUNT`/`SUM`/`MIN`/`MAX`; overview `RSQL_windowfunctions`.
- **Manifest** — `window_pages` section; `test_window_pages_manifest_harvested`. All **27** harvested examples parse under `read=iris` (no `skip_parse` on this batch).

## Changes in `30.11.0+trifour.9`

- **Aggregate function doc fixtures** — harvested [RSQL_AGGREGATE_FUNCTIONS](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_AGGREGATE_FUNCTIONS) child pages: `AVG`, `COUNT`, `SUM`, `MIN`, `MAX`, `%DLIST`, `LIST`, `XMLAGG`, `JSON_ARRAYAGG`, `APPROX_COUNT_DISTINCT`, `STDDEV`, `VARIANCE`, plus `RSQL_aggregatefunctions` overview.
- **Manifest** — `aggregate_pages` section; `test_aggregate_pages_manifest_harvested`.
- **Known gaps** (`skip_parse` in fixtures): `%AFTERHAVING` / `%FOREACH` inside aggregate args, `DISTINCT BY` inside `COUNT`/`LIST`/`XMLAGG`/`%DLIST`, `{fn PI}` scalar ODBC escapes in `SELECT` list.

## Changes in `30.11.0+trifour.8`

- **Unique predicate doc fixtures** — harvested [RSQL_PREDICATE_CONDITONS](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_PREDICATE_CONDITONS) child pages: `%FIND`, `%INSET`, `%INLIST`, `%MATCHES`, `FOR SOME`, `FOR SOME %ELEMENT`, `IS JSON`, `ALL`/`ANY`/`SOME`, `BETWEEN`, `EXISTS`, `IN`, `LIKE`, `NULL`, `%PATTERN`, etc.
- **Parser** — `IrisFind`, `IrisInset`, `IrisInlist` (+ optional `SIZE ((n))`), `IrisMatches`, `IrisForSome`, `IrisForSomeElement`; harvest multiline `<pre>` SQL normalization.
- **Manifest** — `predicate_pages` section; `test_predicate_pages_manifest_harvested`.

## Changes in `30.11.0+trifour.7`

- **String function doc fixtures** — `RSQL_substring`, `RSQL_replace`, `RSQL_position`, `RSQL_trim`, `RSQL_stringmanipulation` (index + composite smoke).
- **Harvest CLI** — `scripts/harvest_iris_doc_sql.py` (`--all-pending` driven by `_manifest.json`).
- **Manifest** — `string_functions` and `clause_pages` sections; `test_string_functions_manifest_harvested`.
- **ODS BMAD** — `tools/bi_utils/scripts/generate_iris_sql_doc_stories.py` + `iris-sql-doc-harvest-registry.yaml` (one story per sql4.md page).

## Changes in `30.11.0+trifour.6`

- **DML doc fixtures** — harvested examples for all six [RSQL_COMMANDS](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_COMMANDS) DML pages: `RSQL_select`, `RSQL_insert`, `RSQL_insertorupdate`, `RSQL_update`, `RSQL_delete`, `RSQL_truncatetable`.
- **Manifest** — `_manifest.json` `dml_commands` section; `test_dml_commands_manifest_harvested` requires at least one parseable example per DML page.
- **Known parser gaps** (documented via `skip_parse` in fixtures): `UPDATE tab (cols) VALUES (...)`, multi-table `DELETE … FROM … FROM …`, synopsis placeholders.

## Changes in `30.11.0+trifour.5`

- **IRIS string / `%` surface** — variadic `STRING(...)`, `%SQLUPPER` / `%EXTERNAL` / other `%NAME(...)` functions, `%STARTSWITH` / `%PATTERN` predicates, `%Dictionary.*` identifiers; `NOT` vs `!` disambiguation in `_parse_range` / `_parse_disjunction`.
- **Function metadata** — `sqlglot/dialects/iris_functions.py` (`IRIS_FUNCTION_LINEAGE`, pseudo-field allowlist).
- **Doc-harvest fixtures** — `tests/dialects/fixtures/iris_doc_sql/*.json` with `doc_key` + `doc_url` per InterSystems RSQL page; `tests/dialects/test_iris_doc_sql.py` parameterized parse tests.

## Changes in `30.11.0+trifour.4`

- **IRIS P2 surface** — contains/follows (`[` / `]`), `SELECT DISTINCT BY (...)`, boolean `!` (OR) / `&` (AND), `%ID` / `%%TABLENAME`, `#` modulo.
- **Parser stall guard** — `Parser._ensure_parse_progress()` on `_parse_column_ops` loops; Iris `_parse_comparison` loop; fails fast with `ParseError` instead of infinite spin when a handler returns without consuming tokens.
- **Dialect tests** — `tests/dialects/conftest.py` 5s `SIGALRM` wall-clock guard; `test_iris_parser_stall_guard` regression.

## Changes in `30.11.0+trifour.3`

- **IRIS P0/P1 dialect** — `read=iris`: `->` Arrow, `%ODBCOUT(...)`, `{d|t|ts '…'}` literals, `INSERT OR UPDATE`, `IS NOT NULL`, `DATEADD('unit', …)`, `TIMESTAMP` type, `IrisGenerator` (no `ENSURE_BOOLS` bool coercion on `&`).
- **Expressions** — `Arrow`, `OdbcOut`, `InsertOrUpdate`, `IrisPercentField`, `ContainsFollows`; `Distinct.by`.
- **Packaging** — explicit `sqlglot/_version.py` via `scripts/write_trifour_version.py` (no setuptools-scm on shallow git clones).

## ODS integration

- Native parse/format: `tools/shared/iris_sql_parse.py` (`parse_iris_sql`, default `read=iris`).
- Legacy masks: `read=tsql` / `iris_ods` via `tools/shared/iris_sqlglot_dialect.py`.
- Corpus harness: `tools/bi_utils/lineage/dw_sql/iris_sql_corpus.py` (dual-path A/B parse rates).
