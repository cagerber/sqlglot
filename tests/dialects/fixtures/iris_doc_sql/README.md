# IRIS doc SQL harvest fixtures

Examples harvested from InterSystems IRIS SQL Reference (2026.1). Each JSON file
corresponds to one `DocBook.UI.Page` (`KEY=RSQL_*` or related).

## Completeness

Compare `doc_key` values across `*.json` in this directory to the page list in
`ods/docs/syntax/sql/sql4.md` (when present) and to:

`https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=<doc_key>`

Future automation should fail if a listed doc page has no fixture file or if
`examples` is empty.

### DML commands (`RSQL_COMMANDS`)

The six core DML pages from
[SQL Commands](https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_COMMANDS)
are tracked in `_manifest.json` under `dml_commands`. `test_dml_commands_manifest_harvested`
requires each to have a fixture with at least one `read=iris`-parseable example.
Synopsis-only blocks from the docs are kept with `skip_parse: true` where noted.

## Schema

```json
{
  "doc_key": "RSQL_concat",
  "doc_url": "https://docs.intersystems.com/iris20261/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_concat",
  "title": "CONCAT (SQL)",
  "doc_version": "2026.1",
  "examples": [
    {
      "id": "nested_concat_fullname",
      "section": "Examples",
      "sql": "SELECT ...",
      "roundtrip": false
    }
  ]
}
```

- `doc_url` — canonical reference for humans and completeness checks.
- `roundtrip` — when `true`, `test_iris_doc_sql` also asserts `sql(dialect=iris)` identity.
