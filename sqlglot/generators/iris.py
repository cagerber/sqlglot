from __future__ import annotations

from sqlglot import exp
from sqlglot.generators.tsql import TSQLGenerator


class IrisGenerator(TSQLGenerator):
    """IRIS-faithful SQL generator (ported from ODS ``Iris_Ods``)."""

    ENSURE_BOOLS = False

    TYPE_MAPPING = {
        **TSQLGenerator.TYPE_MAPPING,
        exp.DType.TIMESTAMP: "TIMESTAMP",
    }

    TRANSFORMS = {
        k: v
        for k, v in TSQLGenerator.TRANSFORMS.items()
        if k not in (exp.CurrentTimestamp, exp.DateAdd)
    }
    TRANSFORMS.update(
        {
            exp.Date: lambda self, e: self._odbc_date_literal_sql(e),
            exp.Time: lambda self, e: self._odbc_time_literal_sql(e),
            exp.Timestamp: lambda self, e: self._odbc_timestamp_literal_sql(e),
        }
    )

    def _odbc_string_literal_sql(self, expression: exp.Expr, prefix: str) -> str:
        inner = expression.this
        if isinstance(inner, exp.Literal) and inner.is_string:
            return f"{{{prefix} '{inner.name}'}}"
        fallback = {"d": "DATE", "t": "TIME", "ts": "TIMESTAMP"}[prefix]
        return self.func(fallback, inner)

    def _odbc_date_literal_sql(self, expression: exp.Date) -> str:
        return self._odbc_string_literal_sql(expression, "d")

    def _odbc_time_literal_sql(self, expression: exp.Time) -> str:
        return self._odbc_string_literal_sql(expression, "t")

    def _odbc_timestamp_literal_sql(self, expression: exp.Timestamp) -> str:
        return self._odbc_string_literal_sql(expression, "ts")

    def arrow_sql(self, expression: exp.Arrow) -> str:
        return f"{self.sql(expression, 'this')}->{self.sql(expression, 'expression')}"

    def odbcout_sql(self, expression: exp.OdbcOut) -> str:
        return f"%ODBCOUT({self.sql(expression, 'this')})"

    def irispercentfield_sql(self, expression: exp.IrisPercentField) -> str:
        prefix = "%%" if expression.args.get("double") else "%"
        return f"{prefix}{self.sql(expression, 'this')}"

    def containsfollows_sql(self, expression: exp.ContainsFollows) -> str:
        op = expression.args.get("op")
        if isinstance(op, exp.Literal) and op.name == "contains":
            return f"{self.sql(expression, 'this')} [{self.sql(expression, 'expression')}"
        return f"{self.sql(expression, 'this')} ] {self.sql(expression, 'expression')}"

    def distinct_sql(self, expression: exp.Distinct) -> str:
        if expression.args.get("by"):
            inner = self.expressions(expression, flat=True)
            return f"DISTINCT BY ({inner})"
        return super().distinct_sql(expression)

    def and_sql(self, expression: exp.And, stack: list[str | exp.Expr] | None = None) -> str:
        if stack is not None:
            return self.connector_sql(expression, "&", stack)
        return f"{self.sql(expression, 'this')} & {self.sql(expression, 'expression')}"

    def or_sql(self, expression: exp.Or, stack: list[str | exp.Expr] | None = None) -> str:
        if stack is not None:
            return self.connector_sql(expression, "!", stack)
        return f"{self.sql(expression, 'this')} ! {self.sql(expression, 'expression')}"

    def mod_sql(self, expression: exp.Mod) -> str:
        return f"{self.sql(expression, 'this')} # {self.sql(expression, 'expression')}"

    def irisstartswith_sql(self, expression: exp.IrisStartswith) -> str:
        return f"{self.sql(expression, 'this')} %STARTSWITH {self.sql(expression, 'expression')}"

    def irispattern_sql(self, expression: exp.IrisPattern) -> str:
        return f"{self.sql(expression, 'this')} %PATTERN {self.sql(expression, 'expression')}"

    def irisfind_sql(self, expression: exp.IrisFind) -> str:
        return f"{self.sql(expression, 'this')} %FIND {self.sql(expression, 'expression')}"

    def irisinset_sql(self, expression: exp.IrisInset) -> str:
        return f"{self.sql(expression, 'this')} %INSET {self.sql(expression, 'expression')}"

    def irisinlist_sql(self, expression: exp.IrisInlist) -> str:
        sql = (
            f"{self.sql(expression, 'this')} %INLIST {self.sql(expression, 'expression')}"
        )
        size = expression.args.get("size")
        if size is not None:
            sql += f" SIZE (({self.sql(size)}))"
        return sql

    def irismatches_sql(self, expression: exp.IrisMatches) -> str:
        return f"{self.sql(expression, 'this')} %MATCHES {self.sql(expression, 'expression')}"

    def irisforsomeelement_sql(self, expression: exp.IrisForSomeElement) -> str:
        collection = self.sql(expression, "collection")
        alias = expression.args.get("alias")
        alias_sql = f" AS {alias}" if alias is not None else ""
        predicate = self.sql(expression, "predicate")
        return f"FOR SOME %ELEMENT({collection}){alias_sql} ({predicate})"

    def irisforsome_sql(self, expression: exp.IrisForSome) -> str:
        tables = expression.args.get("tables") or []
        table_sql = ", ".join(self.sql(t) for t in tables)
        predicate = self.sql(expression, "predicate")
        return f"FOR SOME ({table_sql}) ({predicate})"

    def irisoptimizationhint_sql(self, expression: exp.IrisOptimizationHint) -> str:
        name = self.sql(expression, "this")
        if not name.startswith("%"):
            name = f"%{name}"
        table = expression.args.get("table")
        if table is not None:
            return f"{name} {self.sql(table)}"
        return name

    def iriscurrentof_sql(self, expression: exp.IrisCurrentOf) -> str:
        return f"CURRENT OF {self.sql(expression, 'this')}"

    def irisoptimizedexpression_sql(self, expression: exp.IrisOptimizedExpression) -> str:
        return (
            f"{self.sql(expression, 'hint')} {self.sql(expression, 'this')}"
        )

    def anonymous_sql(self, expression: exp.Anonymous) -> str:
        name = expression.this or ""
        if name.startswith("%"):
            args = self.expressions(expression, flat=True)
            if args:
                return f"{name}({args})"
            return name
        if name.upper() == "NOW" and not expression.expressions:
            return "NOW()"
        return super().anonymous_sql(expression)

    def insertorupdate_sql(self, expression: exp.InsertOrUpdate) -> str:
        hint = self.sql(expression, "hint")
        table = self.sql(expression, "this")
        stored = self.sql(expression, "stored")
        stored = f" {stored}" if stored else ""
        ignore = " IGNORE" if expression.args.get("ignore") else ""
        is_function = expression.args.get("is_function")
        function_kw = " FUNCTION" if is_function else ""
        exists = " IF EXISTS" if expression.args.get("exists") else ""
        where = self.sql(expression, "where")
        where = f"{self.sep()}REPLACE WHERE {where}" if where else ""
        expression_sql = f"{self.sep()}{self.sql(expression, 'expression')}"
        on_conflict = self.sql(expression, "conflict")
        on_conflict = f" {on_conflict}" if on_conflict else ""
        by_name = " BY NAME" if expression.args.get("by_name") else ""
        default_values = "DEFAULT VALUES" if expression.args.get("default") else ""
        returning = self.sql(expression, "returning")

        if self.RETURNING_END:
            expression_sql = f"{expression_sql}{on_conflict}{default_values}{returning}"
        else:
            expression_sql = f"{returning}{expression_sql}{on_conflict}"

        partition_by = self.sql(expression, "partition")
        partition_by = f" {partition_by}" if partition_by else ""
        settings = self.sql(expression, "settings")
        settings = f" {settings}" if settings else ""

        source = self.sql(expression, "source")
        source = f"TABLE {source}" if source else ""

        sql = (
            f"INSERT OR UPDATE{hint}{ignore}{function_kw} {table}{stored}{by_name}{exists}"
            f"{partition_by}{settings}{where}{expression_sql}{source}"
        )
        return self.prepend_ctes(expression, sql)

    def currenttimestamp_sql(self, expression: exp.CurrentTimestamp) -> str:
        this = expression.this
        if this is not None:
            return f"CURRENT_TIMESTAMP({self.sql(this)})"
        return "CURRENT_TIMESTAMP"

    def not_sql(self, expression: exp.Not) -> str:
        inner = expression.this
        if isinstance(inner, exp.Is) and isinstance(inner.expression, exp.Null):
            return f"{self.sql(inner, 'this')} IS NOT NULL"
        return super().not_sql(expression)

    def dateadd_sql(self, expression: exp.DateAdd) -> str:
        unit = expression.args.get("unit")
        unit_sql: str
        if isinstance(unit, exp.Var):
            unit_sql = f"'{unit.name.lower()}'"
        elif isinstance(unit, exp.Literal):
            unit_sql = (
                f"'{unit.name.lower()}'" if unit.is_string else self.sql(unit)
            )
        elif unit is not None:
            unit_sql = self.sql(unit)
        else:
            unit_sql = "'day'"
        return self.func(
            "DATEADD",
            exp.Var(this=unit_sql),
            expression.expression,
            expression.this,
        )
