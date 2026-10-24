from __future__ import annotations

from sqlglot.dialects.tsql import TSQL
from sqlglot.generators.iris import IrisGenerator
from sqlglot.parsers.iris import IrisParser
from sqlglot.tokens import TokenType


class Iris(TSQL):
    """InterSystems IRIS SQL dialect (Trifour fork)."""

    class Tokenizer(TSQL.Tokenizer):
        # IRIS uses double quotes for delimited identifiers; ``[...]`` is contains-predicate syntax.
        IDENTIFIERS = ['"']
        # LONGVARCHAR is an IRIS/ODBC type name (not TEXT / VARCHAR(MAX) on output).
        KEYWORDS = {
            k: v
            for k, v in {
                **TSQL.Tokenizer.KEYWORDS,
                "TIMESTAMP": TokenType.TIMESTAMP,
            }.items()
            if k != "LONGVARCHAR"
        }

    Parser = IrisParser

    Generator = IrisGenerator
