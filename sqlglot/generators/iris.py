from __future__ import annotations

from sqlglot import exp
from sqlglot.generators.tsql import TSQLGenerator


class IrisGenerator(TSQLGenerator):
    """IRIS-faithful SQL generator (ported from ODS ``Iris_Ods``)."""

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
