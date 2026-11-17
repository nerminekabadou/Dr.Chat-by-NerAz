"""Validation of LLM-generated SQL before it reaches the database.

The language model writes the SQL, so its output is untrusted input. The query
is parsed (sqlglot) and accepted only if:

  * it is a single SELECT (UNION / WITH ... SELECT included);
  * it contains no write, DDL or engine command anywhere in its tree;
  * it only reads the tables the chatbot is allowed to use;
  * it only calls functions from an allow-list (no pg_sleep, set_config,
    randomblob, load_extension, file access, ...);
  * it has no recursive CTE and joins at most MAX_TABLE_REFERENCES tables.

A LIMIT is added when missing. This is the first line of defence: the query
then runs on a read-only connection with a time limit (query_runner.py).
See security/README.md for the benchmark behind these rules.
"""

import logging
import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

DEFAULT_ALLOWED_TABLES = frozenset({"doctors", "hospitals", "illnesses", "medications"})
MAX_TABLE_REFERENCES = 4
DEFAULT_LIMIT = 200

# Functions that are not built into sqlglot's typed function set and are safe to call.
SAFE_ANONYMOUS_FUNCTIONS = frozenset({
    "strftime", "date", "time", "datetime", "julianday", "printf", "format", "instr",
    "char", "unicode", "ifnull", "nullif", "iif", "total", "group_concat", "string_agg",
    "date_part", "date_trunc", "to_char", "age", "now", "current_date", "initcap",
})

_FORBIDDEN_NODES = tuple(getattr(exp, name) for name in (
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "Command", "Into",
    "Pragma", "Set", "Copy", "Attach", "Detach", "Use", "Transaction", "Commit", "Rollback",
    "TruncateTable", "Grant", "Revoke", "LoadData",
) if hasattr(exp, name))

_FENCE = re.compile(r"```(?:sqlite|postgresql|postgres|sql)?", re.IGNORECASE)
_DIALECTS = {"postgresql": "postgres", "postgres": "postgres", "sqlite": "sqlite"}

# sqlglot logs a warning when it falls back to a generic Command node; we reject those anyway.
logging.getLogger("sqlglot").setLevel(logging.ERROR)


class UnsafeQueryError(ValueError):
    """Raised when generated SQL is not a single, allowed, read-only query."""


def clean_sql(raw: str) -> str:
    """Strip Markdown fences and whitespace from model output."""
    return _FENCE.sub("", raw).strip().rstrip(";").strip()


def validate_select(raw: str, dialect: str = "sqlite", allowed_tables=DEFAULT_ALLOWED_TABLES) -> str:
    """Return a safe version of the query (with a LIMIT), or raise UnsafeQueryError."""
    read = _DIALECTS.get(dialect, dialect)
    sql = clean_sql(raw)
    if not sql:
        raise UnsafeQueryError("The model did not return a query.")
    try:
        statements = [s for s in sqlglot.parse(sql, read=read) if s is not None]
    except SqlglotError as error:  # ParseError and TokenError (e.g. unterminated strings)
        raise UnsafeQueryError("The query could not be parsed.") from error
    if len(statements) != 1:
        raise UnsafeQueryError("Only a single statement is allowed.")
    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.SetOperation)):
        raise UnsafeQueryError("Only SELECT queries are allowed.")
    for node in tree.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            raise UnsafeQueryError(f"{type(node).__name__} is not allowed.")

    for with_ in tree.find_all(exp.With):
        if with_.args.get("recursive"):
            raise UnsafeQueryError("Recursive queries are not allowed.")

    _check_tables(tree, {t.lower() for t in allowed_tables})
    _check_functions(tree)

    if isinstance(tree, exp.Select) and not tree.args.get("limit"):
        tree = tree.limit(DEFAULT_LIMIT)
    elif isinstance(tree, exp.SetOperation) and not tree.args.get("limit"):
        tree = exp.select("*").from_(tree.subquery("q")).limit(DEFAULT_LIMIT)
    return tree.sql(dialect=read)


def _check_tables(tree, allowed):
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    references = 0
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if not name:  # table-valued function such as pragma_table_info(...)
            raise UnsafeQueryError("Table functions are not allowed.")
        if name in cte_names and not table.db:
            continue
        references += 1
        if table.db or table.catalog:
            raise UnsafeQueryError(f"Schema-qualified table '{table.sql()}' is not allowed.")
        if name not in allowed:
            raise UnsafeQueryError(f"Table '{name}' is not available to the assistant.")
    if references > MAX_TABLE_REFERENCES:
        raise UnsafeQueryError(f"At most {MAX_TABLE_REFERENCES} table references are allowed.")


def _check_functions(tree):
    for func in tree.find_all(exp.Func):
        if isinstance(func, exp.Anonymous):
            name = str(func.this).lower()
            if name not in SAFE_ANONYMOUS_FUNCTIONS:
                raise UnsafeQueryError(f"Function '{name}' is not allowed.")
