"""Validation of LLM-generated SQL before it reaches the database.

The language model writes the SQL, so its output must be treated as untrusted
input. Only a single read-only SELECT (optionally introduced by a CTE) is
allowed. This check is a first line of defence; the database connection is
also opened in read-only mode (see ``app.py``) so that a query slipping past
this filter still cannot modify data.
"""

import re

FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "merge", "drop", "alter", "truncate",
    "create", "grant", "revoke", "copy", "call", "do", "execute",
    "vacuum", "reindex", "lock", "set", "reset", "comment", "into",
)

_FENCE = re.compile(r"```(?:sql)?", re.IGNORECASE)
_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_STRING = re.compile(r"'(?:[^']|'')*'")


class UnsafeQueryError(ValueError):
    """Raised when generated SQL is not a single read-only query."""


def clean_sql(raw: str) -> str:
    """Strip Markdown fences, comments and extra whitespace from model output."""
    sql = _FENCE.sub("", raw)
    sql = _COMMENT.sub(" ", sql)
    sql = " ".join(sql.split())
    return sql.rstrip(";").strip()


def validate_select(raw: str) -> str:
    """Return the cleaned query if it is a single SELECT, else raise."""
    sql = clean_sql(raw)
    if not sql:
        raise UnsafeQueryError("The model did not return a query.")

    # Ignore string literals so that e.g. WHERE name = 'Drop-in clinic' passes.
    code = _STRING.sub("''", sql).lower()

    if ";" in code:
        raise UnsafeQueryError("Only a single statement is allowed.")
    if not re.match(r"^(select|with)\b", code):
        raise UnsafeQueryError("Only SELECT queries are allowed.")
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", code):
            raise UnsafeQueryError(f"Keyword '{keyword.upper()}' is not allowed.")
    return sql
