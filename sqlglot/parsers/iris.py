from __future__ import annotations

from sqlglot import exp
from sqlglot import parser
from sqlglot.parsers.tsql import TSQLParser
from sqlglot.tokens import TokenType


class IrisParser(TSQLParser):
    """IRIS SQL parser on T-SQL base with first-class ``->`` navigation."""

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
