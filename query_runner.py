"""Execute a validated query and format the result for the LLM.

LangChain's SQLDatabase.run() turns rows into dicts, so columns with the same
name (e.g. doctors.name and hospitals.name) overwrite each other. Reading the
cursor directly keeps every column.
"""

import time

from sqlalchemy import text

MAX_ROWS = 50
DEFAULT_TIMEOUT_S = 5  # seconds; stops runaway queries (recursion, huge joins, sleeps)


class QueryTimeout(Exception):
    """The query ran longer than the allowed time."""


def run_query(db, query: str, timeout_s=None) -> str:
    limit = timeout_s if timeout_s is not None else DEFAULT_TIMEOUT_S
    engine = db._engine
    with engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            # Read-only per transaction, on top of the connection default: even if a
            # session setting were changed, this transaction cannot write.
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            if limit:
                connection.exec_driver_sql(f"SET LOCAL statement_timeout = {int(limit * 1000)}")
        raw = connection.connection.dbapi_connection if engine.dialect.name == "sqlite" else None
        if limit and raw is not None:
            deadline = time.monotonic() + limit
            raw.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
        try:
            result = connection.execute(text(query))
            columns = list(result.keys())
            rows = [tuple(row) for row in result.fetchmany(MAX_ROWS)]
        except Exception as error:
            message = str(error).lower()
            if "interrupted" in message or "statement timeout" in message or "canceling statement" in message:
                raise QueryTimeout(f"query exceeded {limit}s") from error
            raise
        finally:
            if raw is not None:
                raw.set_progress_handler(None, 0)
    return f"Columns: {columns}\nRows: {rows}"
