from sqlglot import exp, parse_one
from sqlglot.errors import ParseError
from sqlglot.parsers.iris import IrisParser
from sqlglot.tokens import TokenType
from tests.dialects.test_dialect import Validator


class TestIris(Validator):
    dialect = "iris"

    def test_iris_parser_stall_guard(self):
        real_parse_bracket = IrisParser._parse_bracket

        def stuck_bracket(self, this):
            if self._curr and self._curr.token_type == TokenType.L_BRACKET:
                return this
            return real_parse_bracket(self, this)

        IrisParser._parse_bracket = stuck_bracket
        try:
            with self.assertRaises(ParseError) as ctx:
                parse_one("SELECT t[a] FROM x", read="iris")
            self.assertIn("Parser stuck", str(ctx.exception))
        finally:
            IrisParser._parse_bracket = real_parse_bracket

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

    def test_iris_insert_or_update(self):
        tree = self.parse_one(
            "INSERT OR UPDATE BI_Facts.AdmissionTargets (TargetSeries, HospitalID) "
            "SELECT 'Targets', 1"
        )
        tree.assert_is(exp.InsertOrUpdate)
        self.validate_identity(
            "INSERT OR UPDATE BI_Facts.AdmissionTargets (TargetSeries, HospitalID) "
            "SELECT 'Targets', 1"
        )

    def test_iris_insert_or_update_with_cte(self):
        sql = (
            "WITH pv AS (SELECT 1 AS x) "
            "INSERT OR UPDATE BI_Facts.AdmissionTargets (TargetSeries) SELECT 'Targets'"
        )
        tree = self.parse_one(sql)
        tree.assert_is(exp.InsertOrUpdate)
        self.assertIn("WITH pv AS", tree.sql(dialect="iris"))

    def test_iris_odbcout(self):
        tree = self.parse_one(
            "SELECT %ODBCOUT(t.SubmissionDate) FROM t "
            "WHERE COALESCE(%ODBCOUT(CAST(ep.AdmissionDateTime AS DATE)), '') <> ''"
        )
        tree.assert_is(exp.Select)
        odbcout = tree.expressions[0]
        odbcout.assert_is(exp.OdbcOut)
        self.validate_identity(
            "COALESCE(%ODBCOUT(CAST(x AS DATE)), '')",
            "COALESCE(%ODBCOUT(CAST(x AS DATE)), '')",
        )

    def test_iris_percent_pseudo_fields(self):
        tree = self.parse_one("SELECT %ID, %%TABLENAME FROM BI_Facts.T")
        tree.assert_is(exp.Select)
        fields = tree.expressions
        fields[0].assert_is(exp.IrisPercentField)
        fields[1].assert_is(exp.IrisPercentField)
        self.assertTrue(fields[1].args.get("double"))
        self.validate_identity("SELECT %ID, %%TABLENAME FROM BI_Facts.T")

    def test_iris_distinct_by(self):
        tree = self.parse_one("SELECT DISTINCT BY (a, b) FROM t")
        tree.assert_is(exp.Select)
        distinct = tree.args["distinct"]
        distinct.assert_is(exp.Distinct)
        self.assertTrue(distinct.args.get("by"))
        self.validate_identity("SELECT DISTINCT BY (a, b) FROM t")

    def test_iris_contains_follows(self):
        contains = self.parse_one("SELECT * FROM t WHERE Name ['Smith'")
        cf = contains.find(exp.ContainsFollows)
        self.assertIsNotNone(cf)
        self.validate_identity("SELECT * FROM t WHERE Name ['Smith'")

        follows = self.parse_one("SELECT * FROM t WHERE Name ] 'Jones'")
        ff = follows.find(exp.ContainsFollows)
        self.assertIsNotNone(ff)
        self.validate_identity("SELECT * FROM t WHERE Name ] 'Jones'")

    def test_iris_boolean_operators(self):
        and_tree = self.parse_one("SELECT * FROM t WHERE a & b")
        self.assertIsInstance(and_tree.find(exp.Where).this, exp.And)
        self.validate_identity("SELECT * FROM t WHERE a & b")

        or_tree = self.parse_one("SELECT * FROM t WHERE a ! b")
        self.assertIsInstance(or_tree.find(exp.Where).this, exp.Or)
        self.validate_identity("SELECT * FROM t WHERE a ! b")

    def test_iris_hash_modulo(self):
        tree = self.parse_one("SELECT 10 # 3 AS rem")
        mod = tree.find(exp.Mod)
        self.assertIsNotNone(mod)
        self.validate_identity("SELECT 10 # 3 AS rem")

    def test_iris_string_variadic(self):
        tree = self.parse_one("SELECT STRING('a','b','c')")
        concat = tree.find(exp.Concat)
        self.assertIsNotNone(concat)
        self.assertEqual(len(concat.expressions), 3)

    def test_iris_percent_sql_functions(self):
        tree = self.parse_one("SELECT %SQLUPPER(Name), %EXTERNAL(FavoriteColors) FROM t")
        anon = tree.find_all(exp.Anonymous)
        names = {a.this for a in anon}
        self.assertIn("%SQLUPPER", names)
        self.assertIn("%EXTERNAL", names)
        self.validate_identity("SELECT %SQLUPPER(Name) FROM t")

    def test_iris_startswith_and_pattern(self):
        sw = self.parse_one(
            "SELECT Name FROM Sample.MyTest WHERE Name %STARTSWITH 'M'"
        )
        sw.find(exp.IrisStartswith).assert_is(exp.IrisStartswith)
        self.validate_identity(
            "SELECT Name FROM Sample.MyTest WHERE Name %STARTSWITH 'M'"
        )

        pat = self.parse_one(
            "SELECT Name,Home_State FROM Sample.Person WHERE Home_State %PATTERN '1U1\"C\"'"
        )
        pat.find(exp.IrisPattern).assert_is(exp.IrisPattern)

    def test_iris_not_startswith(self):
        tree = self.parse_one(
            "SELECT Name FROM Sample.MyTest WHERE NOT Name %STARTSWITH 'M'"
        )
        not_expr = tree.find(exp.Not)
        self.assertIsNotNone(not_expr)
        self.assertIsInstance(not_expr.this, exp.IrisStartswith)

    def test_iris_dictionary_identifier(self):
        tree = self.parse_one("SELECT * FROM %Dictionary.ClassDefinition")
        self.assertIsNotNone(tree.find(exp.Table))
        parse_one("SELECT * FROM %Dictionary.ClassDefinition", read="iris")

    def test_iris_unique_predicates(self):
        inlist = self.parse_one(
            "SELECT Name FROM Sample.Person WHERE Home_State %INLIST $LISTBUILD('VT','NH')"
        )
        inlist.find(exp.IrisInlist).assert_is(exp.IrisInlist)

        find = self.parse_one(
            "SELECT Name FROM Sample.Person WHERE Age %FIND Sample.Person_AgeIndex"
        )
        find.find(exp.IrisFind).assert_is(exp.IrisFind)

        inset = self.parse_one(
            "SELECT Name FROM Sample.Person WHERE Home_State %INSET Sample.Person_StateIndex"
        )
        inset.find(exp.IrisInset).assert_is(exp.IrisInset)

        matches = self.parse_one(
            "SELECT Name FROM Sample.Person WHERE Name %MATCHES 'Mc*'"
        )
        matches.find(exp.IrisMatches).assert_is(exp.IrisMatches)

        element = self.parse_one(
            "SELECT Name FROM Sample.Person WHERE FOR SOME %ELEMENT(FavoriteColors) (%VALUE='Red')"
        )
        element.find(exp.IrisForSomeElement).assert_is(exp.IrisForSomeElement)

        forsome = self.parse_one(
            "SELECT Name FROM Sample.Person AS p WHERE FOR SOME (Sample.Employee AS e)(e.Name=p.Name)"
        )
        forsome.find(exp.IrisForSome).assert_is(exp.IrisForSome)

    def test_iris_datatypes(self):
        self.parse_one("CREATE TABLE t (FirstName %String(MAXLEN=30))")
        self.parse_one("CREATE TABLE t (Born %Library.Date(MINVAL=-672045))")
        self.parse_one(
            'CREATE TABLE t (MyTS TIMESTAMP(MINVAL="1492-01-01 00:00:00"))'
        )
        self.parse_one("CREATE TABLE t (Label Sample.TruncStr(MAXLEN=10))")
        self.validate_identity("CREATE TABLE t (x POSIXTIME)")
        self.validate_identity("CREATE TABLE t (x ROWVERSION)")
        self.validate_identity("CREATE TABLE t (x SERIAL)")
        self.validate_identity("CREATE TABLE t (x GUID)")
        self.validate_identity("CREATE TABLE t (x UNIQUEIDENTIFIER)")
        self.validate_identity("CREATE TABLE t (x LONGVARCHAR)")
        self.validate_identity("CREATE TABLE t (x LONGVARBINARY)")
        self.validate_identity("CREATE TABLE t (x OREF)")
        self.validate_identity("CREATE TABLE t (x VECTOR(FLOAT, 128))")
        self.validate_identity("CREATE TABLE t (x VARCHAR(MAX))")
        self.validate_identity("CREATE TABLE t (x NUMERIC(6, 2))")
        self.validate_identity("CREATE TABLE t (x TIME(3))")
        self.validate_identity("CREATE TABLE t (x VARCHAR(''))")
        self.validate_identity("CREATE TABLE t (x VARBINARY(''))")
        self.validate_identity("CAST(x AS POSIXTIME)")
        self.parse_one("CAST(x AS VECTOR(DOUBLE, 64))")

    def test_iris_optimization_hints(self):
        doruntime = self.parse_one("SELECT %DORUNTIME Name FROM Sample.Person")
        doruntime.find(exp.IrisOptimizationHint).assert_is(exp.IrisOptimizationHint)
        self.validate_identity("SELECT %DORUNTIME Name FROM Sample.Person")

        noruntime = self.parse_one("SELECT %NORUNTIME * FROM Sample.Person")
        noruntime.find(exp.IrisOptimizationHint).assert_is(exp.IrisOptimizationHint)

        inorder = self.parse_one("SELECT Name FROM %INORDER Sample.Person")
        table = inorder.find(exp.Table)
        self.assertIsNotNone(table)
        hints = table.args.get("hints") or []
        self.assertTrue(any(isinstance(h, exp.IrisOptimizationHint) for h in hints))

        firsttable = self.parse_one(
            "SELECT * FROM %FIRSTTABLE P Sample.Employee AS E JOIN Sample.Person AS P ON E.Name = P.Name"
        )
        ft_table = firsttable.find(exp.Table)
        ft_hints = ft_table.args.get("hints") or []
        ft_hint = next(h for h in ft_hints if isinstance(h, exp.IrisOptimizationHint))
        self.assertIsNotNone(ft_hint.args.get("table"))

        noindex = self.parse_one(
            "SELECT Name FROM Sample.Person WHERE %NOINDEX Age >= 18"
        )
        noindex.find(exp.IrisOptimizedExpression).assert_is(exp.IrisOptimizedExpression)

        comment = self.parse_one(
            "/* %NOINDEX */ SELECT Name FROM Sample.Person WHERE Age >= 18"
        )
        self.assertIsNotNone(comment.find(exp.Select))

    def test_iris_where_current_of(self):
        delete = self.parse_one(
            "DELETE FROM Sample.Employees WHERE CURRENT OF EmployeeCursor"
        )
        delete.find(exp.IrisCurrentOf).assert_is(exp.IrisCurrentOf)
        self.validate_identity(
            "DELETE FROM Sample.Employees WHERE CURRENT OF EmployeeCursor"
        )
        update = self.parse_one(
            "UPDATE SQLUser.WordPairs SET Lang = 'Es' WHERE CURRENT OF WPCursor"
        )
        update.find(exp.IrisCurrentOf).assert_is(exp.IrisCurrentOf)
