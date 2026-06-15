from __future__ import annotations

import typing as t

from sqlglot import exp
from sqlglot import parser
from sqlglot.helper import ensure_list
from sqlglot.dialects.iris_functions import (
    IRIS_FROM_OPTIMIZATION_HINTS,
    IRIS_PSEUDO_FIELD_NAMES,
    IRIS_SELECT_OPTIMIZATION_HINTS,
    IRIS_WHERE_OPTIMIZATION_HINTS,
)
from sqlglot.parsers.tsql import TSQLParser
from sqlglot.tokens import TokenType


class IrisParser(TSQLParser):
    """IRIS SQL parser on T-SQL base with first-class IRIS surface forms."""

    FUNC_TOKENS = {
        *TSQLParser.FUNC_TOKENS,
        TokenType.DATABASE,
        TokenType.SCHEMA,
    }

    FUNCTIONS = {
        **TSQLParser.FUNCTIONS,
        # IRIS STRING is variadic concatenation, not T-SQL timestamp STRING.
        "STRING": lambda args, dialect: exp.Concat(expressions=args),
        "NOW": lambda args, dialect: exp.Anonymous(this="NOW"),
        "DATABASE": lambda args, dialect: exp.Anonymous(this="DATABASE", expressions=args),
    }

    UNARY_PARSERS = {
        k: v
        for k, v in TSQLParser.UNARY_PARSERS.items()
        if k != TokenType.NOT
    }

    DISJUNCTION = {
        k: v for k, v in TSQLParser.DISJUNCTION.items() if k != TokenType.NOT
    }

    CONJUNCTION = {
        **TSQLParser.CONJUNCTION,
        TokenType.AMP: exp.And,
    }

    BITWISE = {
        k: v for k, v in TSQLParser.BITWISE.items() if k != TokenType.AMP
    }

    TERM = {
        k: v
        for k, v in {
            **TSQLParser.TERM,
            TokenType.HASH: exp.Mod,
        }.items()
        if k != TokenType.MOD
    }

    COLUMN_OPERATORS = {
        **{
            k: v
            for k, v in parser.Parser.COLUMN_OPERATORS.items()
            if k
            not in (
                TokenType.ARROW,
                TokenType.DARROW,
                TokenType.HASH_ARROW,
                TokenType.DHASH_ARROW,
            )
        },
        TokenType.DOT: None,
        TokenType.ARROW: lambda self, this, path: self.expression(
            exp.Arrow(this=this, expression=path)
        ),
    }

    def _iris_contains_follows_bracket_ahead(self) -> bool:
        return bool(
            self._curr
            and self._curr.token_type == TokenType.L_BRACKET
            and self._next
            and self._next.token_type in (TokenType.STRING, TokenType.NUMBER)
        )

    def _parse_column_ops(self, this: exp.Expr | None) -> exp.Expr | None:
        while self._curr and self._curr.token_type in self.BRACKETS:
            if this is not None and self._iris_contains_follows_bracket_ahead():
                break
            index = self._index
            this = self._parse_bracket(this)
            self._ensure_parse_progress(index, "iris column_ops brackets")

        column_operators = self.COLUMN_OPERATORS
        cast_column_operators = self.CAST_COLUMN_OPERATORS
        while self._curr:
            index = self._index
            op_token = self._curr.token_type

            if op_token not in column_operators:
                break
            op = column_operators[op_token]
            self._advance()

            if op_token in cast_column_operators:
                field = self._parse_dcolon()
                if not field:
                    self.raise_error("Expected type")
            elif op and self._curr:
                field = self._parse_column_reference() or self._parse_bitwise()
                if isinstance(field, exp.Column) and self._match(TokenType.DOT, advance=False):
                    field = self._parse_column_ops(field)
            else:
                field = self._parse_field(any_token=True, anonymous_func=True)

            if isinstance(field, (exp.Func, exp.Window)) and this:
                this = this.transform(
                    lambda n: n.to_dot(include_dots=False) if isinstance(n, exp.Column) else n
                )

            if op:
                this = op(self, this, field)
            elif isinstance(this, exp.Column) and not this.args.get("catalog") and isinstance(field, (exp.Column, exp.Identifier)):
                this = self.expression(
                    exp.Column(
                        this=field,
                        table=this.this,
                        db=this.args.get("table"),
                        catalog=this.args.get("db"),
                    ),
                    comments=this.comments,
                )
            elif isinstance(field, exp.Window):
                window_func = self.expression(exp.Dot(this=this, expression=field.this))
                field.set("this", window_func)
                this = field
            else:
                this = self.expression(exp.Dot(this=this, expression=field))

            if field and field.comments:
                t.cast(exp.Expr, this).add_comments(field.pop_comments())

            if not (this is not None and self._iris_contains_follows_bracket_ahead()):
                this = self._parse_bracket(this)

            self._ensure_parse_progress(index, "iris column_ops")

        return this

    def _parse_range(self, this: exp.Expr | None = None) -> exp.Expr | None:
        this = this or self._parse_bitwise()
        negate = (
            self._match(TokenType.NOT, advance=False)
            and (self._curr.text or "").upper() == "NOT"
        )
        if negate:
            self._advance()

        if self._match_set(self.RANGE_PARSERS):
            expression = self.RANGE_PARSERS[self._prev.token_type](self, this)
            if not expression:
                return this
            this = expression
        elif self._match(TokenType.ISNULL) or (negate and self._match(TokenType.NULL)):
            this = self.expression(exp.Is(this=this, expression=exp.Null()))

        if self._match(TokenType.NOTNULL):
            this = self.expression(exp.Is(this=this, expression=exp.Null()))
            this = self.expression(exp.Not(this=this))

        if negate:
            this = self._negate_range(this)

        if self._match(TokenType.IS):
            this = self._parse_is(this)

        return this

    def _parse_disjunction(self) -> exp.Expr | None:
        this = self._parse_conjunction()
        while True:
            if self._match(TokenType.NOT):
                if (self._prev.text or "").upper() == "NOT":
                    self._retreat(self._index - 1)
                    break
                comments = self._prev_comments
                this = self.expression(
                    exp.Or(this=this, expression=self._parse_conjunction()),
                    comments=comments,
                )
            elif self._match_set(self.DISJUNCTION):
                comments = self._prev_comments
                this = self.expression(
                    self.DISJUNCTION[self._prev.token_type](
                        this=this, expression=self._parse_conjunction()
                    ),
                    comments=comments,
                )
            else:
                break
        return this

    def _parse_equality(self) -> exp.Expr | None:
        if (
            self._match(TokenType.NOT, advance=False)
            and (self._curr.text or "").upper() == "NOT"
        ):
            self._advance()
            inner = self._parse_equality()
            if inner is None:
                return None
            return self.expression(exp.Not(this=inner))
        return super()._parse_equality()

    def _parse_distinct_on_select(self, matched_distinct: bool) -> exp.Distinct | None:
        if not matched_distinct:
            return None
        if self._match_text_seq("BY"):
            return self.expression(
                exp.Distinct(
                    expressions=self._parse_wrapped_csv(self._parse_assignment),
                    by=True,
                )
            )
        return super()._parse_distinct_on_select(matched_distinct)

    def _parse_iris_optimization_hint_name(
        self, allowed: frozenset[str]
    ) -> exp.IrisOptimizationHint | None:
        index = self._index
        if not self._match(TokenType.MOD):
            return None
        if not self._match(TokenType.VAR):
            self._retreat(index)
            return None
        name = self._prev.text.upper()
        if name not in allowed:
            self._retreat(index)
            return None
        table = None
        if name == "FIRSTTABLE":
            table = self._parse_id_var(any_token=False, tokens={TokenType.VAR})
        return self.expression(
            exp.IrisOptimizationHint(this=exp.var(name), table=table)
        )

    def _parse_iris_from_optimization_hints(self) -> list[exp.Expr]:
        hints: list[exp.Expr] = []
        while True:
            hint = self._parse_iris_optimization_hint_name(IRIS_FROM_OPTIMIZATION_HINTS)
            if hint is None:
                break
            hints.append(hint)
        return hints

    def _parse_iris_select_optimization_hint(self) -> exp.IrisOptimizationHint | None:
        return self._parse_iris_optimization_hint_name(IRIS_SELECT_OPTIMIZATION_HINTS)

    def _parse_iris_where_optimization_hint(self) -> exp.IrisOptimizationHint | None:
        return self._parse_iris_optimization_hint_name(IRIS_WHERE_OPTIMIZATION_HINTS)

    def _parse_projections(self) -> t.Tuple[list[exp.Expr], bool]:
        leading: list[exp.Expr] = []
        while True:
            hint = self._parse_iris_select_optimization_hint()
            if hint is None:
                break
            leading.append(hint)
        projections, exclude = super()._parse_projections()
        if leading:
            self._iris_pending_select_hints = leading
        return projections, exclude

    def _parse_select_query(
        self,
        nested: bool = False,
        table: bool = False,
        parse_subquery_alias: bool = True,
        parse_set_operation: bool = True,
    ) -> exp.Expr | None:
        self._iris_pending_select_hints = None
        result = super()._parse_select_query(
            nested=nested,
            table=table,
            parse_subquery_alias=parse_subquery_alias,
            parse_set_operation=parse_set_operation,
        )
        pending = getattr(self, "_iris_pending_select_hints", None)
        if pending and isinstance(result, exp.Select):
            mods = list(result.args.get("operation_modifiers") or [])
            result.set("operation_modifiers", pending + mods)
            self._iris_pending_select_hints = None
        return result

    def _parse_table(
        self,
        schema: bool = False,
        joins: bool = False,
        alias_tokens: t.Collection[TokenType] | None = None,
        parse_bracket: bool = False,
        is_db_reference: bool = False,
        parse_partition: bool = False,
        consume_pipe: bool = False,
    ) -> exp.Expr | None:
        from_hints: list[exp.Expr] = []
        if not schema and not is_db_reference and not consume_pipe and not joins:
            from_hints = self._parse_iris_from_optimization_hints()
        table = super()._parse_table(
            schema=schema,
            joins=joins,
            alias_tokens=alias_tokens,
            parse_bracket=parse_bracket,
            is_db_reference=is_db_reference,
            parse_partition=parse_partition,
            consume_pipe=consume_pipe,
        )
        if from_hints and isinstance(table, exp.Table):
            existing = list(table.args.get("hints") or [])
            table.set("hints", from_hints + existing)
        return table

    def _parse_percent_prefixed_atom(self) -> exp.Expr | None:
        if not self._match(TokenType.MOD):
            return None

        start = self._index - 1

        if self._match(TokenType.MOD):
            if self._match(TokenType.VAR):
                return self.expression(
                    exp.IrisPercentField(this=self._prev.text, double=True)
                )
            self._retreat(start)
            return None

        if (
            self._curr
            and self._curr.token_type == TokenType.VAR
            and self._curr.text.upper() == "ODBCOUT"
            and self._next
            and self._next.token_type == TokenType.L_PAREN
        ):
            self._advance()
            self._match(TokenType.L_PAREN)
            this = self._parse_assignment()
            self._match_r_paren()
            return self.expression(exp.OdbcOut(this=this))

        if self._match(TokenType.VAR):
            name = self._prev.text.upper()
            if name in IRIS_PSEUDO_FIELD_NAMES:
                return self.expression(exp.IrisPercentField(this=name, double=False))
            self._retreat(start)
            return None

        self._retreat(start)
        return None

    def _parse_iris_percent_function(self) -> exp.Expr | None:
        index = self._index
        if not self._match(TokenType.MOD):
            return None
        if not self._curr or self._curr.token_type != TokenType.VAR:
            self._retreat(index)
            return None
        if not self._next or self._next.token_type != TokenType.L_PAREN:
            self._retreat(index)
            return None
        name = self._curr.text.upper()
        self._advance()
        self._match(TokenType.L_PAREN)
        args = self._parse_csv(self._parse_assignment)
        self._match_r_paren()
        return exp.Anonymous(this=f"%{name}", expressions=args)

    def _try_parse_iris_percent_predicate(self, this: exp.Expr) -> exp.Expr | None:
        index = self._index
        if not self._match(TokenType.MOD):
            return None
        if self._match_text_seq("STARTSWITH"):
            return self.expression(
                exp.IrisStartswith(this=this, expression=self._parse_range())
            )
        if self._match_text_seq("PATTERN"):
            return self.expression(
                exp.IrisPattern(this=this, expression=self._parse_range())
            )
        if self._match_text_seq("FIND"):
            return self.expression(
                exp.IrisFind(this=this, expression=self._parse_range())
            )
        if self._match_text_seq("INSET"):
            return self.expression(
                exp.IrisInset(this=this, expression=self._parse_range())
            )
        if self._match_text_seq("INLIST"):
            valueset = self._parse_range()
            size = None
            if self._match_text_seq("SIZE"):
                self._match_l_paren()
                self._match_l_paren()
                size = self._parse_number()
                self._match_r_paren()
                self._match_r_paren()
            return self.expression(
                exp.IrisInlist(this=this, expression=valueset, size=size)
            )
        if self._match_text_seq("MATCHES"):
            return self.expression(
                exp.IrisMatches(this=this, expression=self._parse_range())
            )
        self._retreat(index)
        return None

    def _parse_iris_for_some(self) -> exp.Expr | None:
        index = self._index
        if not self._match_text_seq("FOR", "SOME"):
            return None
        if self._match(TokenType.MOD) and self._match_text_seq("ELEMENT"):
            self._match_l_paren()
            collection = self._parse_column()
            self._match_r_paren()
            alias = self._parse_id_var() if self._match(TokenType.ALIAS) else None
            self._match_l_paren()
            predicate = self._parse_assignment()
            self._match_r_paren()
            return self.expression(
                exp.IrisForSomeElement(
                    collection=collection, predicate=predicate, alias=alias
                )
            )
        if not self._match(TokenType.L_PAREN):
            self._retreat(index)
            return None
        tables = [self._parse_table()]
        while self._match(TokenType.COMMA):
            tables.append(self._parse_table())
        self._match_r_paren()
        self._match_l_paren()
        predicate = self._parse_assignment()
        self._match_r_paren()
        return self.expression(exp.IrisForSome(tables=tables, predicate=predicate))

    def _parse_id_var(
        self,
        any_token: bool = True,
        tokens: t.Collection[TokenType] | None = None,
    ) -> exp.Expr | None:
        if self._match(TokenType.MOD, advance=False):
            if self._next and self._next.token_type == TokenType.VAR:
                name = self._next.text.upper()
                next_tt = (
                    self._tokens[self._index + 2].token_type
                    if self._index + 2 < len(self._tokens)
                    else None
                )
                if name not in IRIS_PSEUDO_FIELD_NAMES or next_tt in (
                    TokenType.DOT,
                    TokenType.L_PAREN,
                ):
                    self._advance()
                    self._advance()
                    return exp.to_identifier(f"%{self._prev.text}")
                self._advance()
                self._advance()
                return self.expression(exp.IrisPercentField(this=name, double=False))
        return super()._parse_id_var(any_token=any_token, tokens=tokens)

    def _parse_factor(self) -> exp.Expr | None:
        percent = self._parse_percent_prefixed_atom()
        if percent is not None:
            return percent
        return super()._parse_factor()

    def _parse_unary(self) -> exp.Expr | None:
        for_some = self._parse_iris_for_some()
        if for_some is not None:
            return for_some
        where_hint = self._parse_iris_where_optimization_hint()
        if where_hint is not None:
            inner = super()._parse_unary()
            if inner is None:
                return None
            return self.expression(
                exp.IrisOptimizedExpression(hint=where_hint, this=inner)
            )
        percent = self._parse_percent_prefixed_atom()
        if percent is not None:
            return percent
        func = self._parse_iris_percent_function()
        if func is not None:
            return func
        return super()._parse_unary()

    def _parse_comparison(self) -> exp.Expr | None:
        this = self._parse_range()
        while True:
            index = self._index
            if self._match(TokenType.L_BRACKET):
                comments = self._prev_comments
                this = self.expression(
                    exp.ContainsFollows(
                        this=this,
                        expression=self._parse_range(),
                        op=exp.Literal.string("contains"),
                    ),
                    comments=comments,
                )
                self._ensure_parse_progress(index, "iris comparison contains")
                continue
            if self._match(TokenType.R_BRACKET):
                comments = self._prev_comments
                this = self.expression(
                    exp.ContainsFollows(
                        this=this,
                        expression=self._parse_range(),
                        op=exp.Literal.string("follows"),
                    ),
                    comments=comments,
                )
                self._ensure_parse_progress(index, "iris comparison follows")
                continue
            iris_pred = self._try_parse_iris_percent_predicate(this)
            if iris_pred is not None:
                this = iris_pred
                self._ensure_parse_progress(index, "iris comparison percent predicate")
                continue
            if not self._match_set(self.COMPARISON):
                break
            comments = self._prev_comments
            this = self.expression(
                self.COMPARISON[self._prev.token_type](this=this, expression=self._parse_range()),
                comments=comments,
            )
            self._ensure_parse_progress(index, "iris comparison")
        return this

    def _parse_iris_named_type_param(self) -> exp.EQ | None:
        index = self._index
        if not (self._curr and self._curr.token_type == TokenType.VAR):
            return None
        if not (self._next and self._next.token_type == TokenType.EQ):
            return None
        name = self._curr.text
        self._advance()
        self._match(TokenType.EQ)
        value = self._parse_assignment()
        if value is None:
            self._retreat(index)
            return None
        return self.expression(exp.EQ(this=exp.var(name), expression=value))

    def _parse_iris_class_datatype(self) -> exp.DataType | None:
        index = self._index
        if not self._match(TokenType.MOD):
            return None
        if not self._curr or self._curr.token_type not in (TokenType.VAR, TokenType.TEXT):
            self._retreat(index)
            return None
        self._advance()
        name = self._prev.text
        while self._match(TokenType.DOT):
            if not self._curr or self._curr.token_type not in (TokenType.VAR, TokenType.TEXT):
                self._retreat(index)
                return None
            self._advance()
            name = f"{name}.{self._prev.text}"
        type_name = f"%{name}"
        expressions = None
        if self._match(TokenType.L_PAREN):
            expressions = self._parse_csv(self._parse_type_size)
            if not self._match(TokenType.R_PAREN):
                self._retreat(index)
                return None
        return self.expression(
            exp.DataType(
                this=exp.DType.USERDEFINED,
                kind=type_name,
                expressions=expressions,
            )
        )

    def _parse_type_size(self) -> exp.DataTypeParam | exp.EQ | None:
        named = self._parse_iris_named_type_param()
        if named is not None:
            return named
        index = self._index
        if self._match(TokenType.STRING):
            if self._prev.text == "":
                return exp.DataTypeParam(this=exp.Literal.string(""))
            self._retreat(index)
        return super()._parse_type_size()

    def _parse_types(
        self,
        check_func: bool = False,
        schema: bool = False,
        allow_identifiers: bool = True,
        with_collation: bool = False,
    ) -> exp.Expr | None:
        index = self._index
        class_type = self._parse_iris_class_datatype()
        if class_type is not None:
            return class_type
        return super()._parse_types(
            check_func=check_func,
            schema=schema,
            allow_identifiers=allow_identifiers,
            with_collation=with_collation,
        )

    def _parse_insert(self) -> exp.Insert | exp.MultitableInserts | exp.InsertOrUpdate:
        comments: list[str] = []
        hint = self._parse_hint()
        overwrite = self._match(TokenType.OVERWRITE)
        ignore = self._match(TokenType.IGNORE)
        local = self._match_text_seq("LOCAL")
        alternative = None
        is_function = None
        insert_or_update = False

        if self._match_text_seq("DIRECTORY"):
            this: exp.Expr | None = self.expression(
                exp.Directory(
                    this=self._parse_var_or_string(),
                    local=local,
                    row_format=self._parse_row_format(match_row=True),
                )
            )
        else:
            if self._match_set((TokenType.FIRST, TokenType.ALL)):
                comments += ensure_list(self._prev_comments)
                return self._parse_multitable_inserts(comments)

            if self._match(TokenType.OR):
                if self._match(TokenType.UPDATE):
                    insert_or_update = True
                else:
                    alternative = self._match_texts(self.INSERT_ALTERNATIVES) and self._prev.text

            self._match(TokenType.INTO)
            comments += ensure_list(self._prev_comments)
            self._match(TokenType.TABLE)
            is_function = self._match(TokenType.FUNCTION)

            this = self._parse_function() if is_function else self._parse_insert_table()

        returning = self._parse_returning()

        insert_cls = exp.InsertOrUpdate if insert_or_update else exp.Insert
        return self.expression(
            insert_cls(
                hint=hint,
                is_function=is_function,
                this=this,
                stored=self._match_text_seq("STORED") and self._parse_stored(),
                by_name=self._match_text_seq("BY", "NAME"),
                exists=self._parse_exists(),
                where=self._match_pair(TokenType.REPLACE, TokenType.WHERE)
                and self._parse_disjunction(),
                partition=self._match(TokenType.PARTITION_BY) and self._parse_partitioned_by(),
                settings=self._match_text_seq("SETTINGS") and self._parse_settings_property(),
                default=self._match_text_seq("DEFAULT", "VALUES"),
                expression=self._parse_derived_table_values() or self._parse_ddl_select(),
                conflict=self._parse_on_conflict(),
                returning=returning or self._parse_returning(),
                overwrite=overwrite,
                alternative=alternative,
                ignore=ignore,
                source=self._match(TokenType.TABLE) and self._parse_table(),
            ),
            comments=comments,
        )

    def _parse_where(self, skip_where_token: bool = False) -> exp.Where | None:
        if not skip_where_token and not self._match(TokenType.WHERE):
            return None

        comments = self._prev_comments
        if self._match_text_seq("CURRENT", "OF"):
            cursor = self._parse_id_var()
            return self.expression(
                exp.Where(this=self.expression(exp.IrisCurrentOf(this=cursor))),
                comments=comments,
            )
        return self.expression(
            exp.Where(this=self._parse_disjunction()),
            comments=comments,
        )
