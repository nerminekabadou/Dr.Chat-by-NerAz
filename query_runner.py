"""Execute a validated query and format the result for the LLM.

LangChain's SQLDatabase.run() turns rows into dicts, so columns with the same
name (e.g. doctors.name and hospitals.name) overwrite each other. Reading the
cursor directly keeps every column.
"""

from sqlalchemy import text

MAX_ROWS = 50


def run_query(db, query: str) -> str:
    with db._engine.connect() as connection:
        result = connection.execute(text(query))
        columns = list(result.keys())
        rows = [tuple(row) for row in result.fetchmany(MAX_ROWS)]
    return f"Columns: {columns}\nRows: {rows}"
