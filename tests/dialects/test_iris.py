from sqlglot import exp, parse_one
from tests.dialects.test_dialect import Validator


class TestIris(Validator):
    dialect = "iris"

    def test_iris_arrow(self):
        tree = self.parse_one("SELECT e->PatientID FROM t e")
        tree.assert_is(exp.Select)
        arrow = tree.expressions[0]
        arrow.assert_is(exp.Arrow)
        self.assertEqual(
            "SELECT e->PatientID FROM t AS e",
            tree.sql(dialect="iris"),
        )

        chained = self.parse_one("SELECT Film->Category->CategoryName FROM Film")
        inner = chained.expressions[0]
        inner.assert_is(exp.Arrow)
        self.assertIsInstance(inner.this, exp.Arrow)

    def test_iris_odbc_datetime_literals(self):
        self.validate_identity("SELECT 1 WHERE d = {d '2024-06-15'}")
        self.validate_identity("SELECT 1 WHERE t = {t '12:30:00'}")
        self.validate_identity("SELECT 1 WHERE ts = {ts '2024-06-15 12:30:00'}")

    def test_iris_timestamp_type(self):
        self.validate_identity("CAST(NULL AS TIMESTAMP)")

    def test_iris_current_timestamp(self):
        self.validate_identity("SELECT CURRENT_TIMESTAMP")

    def test_iris_dateadd_quoted_unit(self):
        self.validate_identity("SELECT DATEADD('minute', 5, x)")

    def test_iris_is_not_null(self):
        self.validate_identity("SELECT * FROM t WHERE x IS NOT NULL")
