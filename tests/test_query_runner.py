from langchain_community.utilities import SQLDatabase
from sqlalchemy import text

from query_runner import run_query


def test_keeps_columns_with_the_same_name(tmp_path):
    db = SQLDatabase.from_uri(f"sqlite:///{tmp_path / 'h.db'}")
    with db._engine.begin() as c:
        c.execute(text("CREATE TABLE hospitals (id INTEGER, name TEXT)"))
        c.execute(text("CREATE TABLE doctors (name TEXT, hospital_id INTEGER)"))
        c.execute(text("INSERT INTO hospitals VALUES (1, 'Clinique du Lac')"))
        c.execute(text("INSERT INTO doctors VALUES ('Dr. Amira', 1)"))
    out = run_query(db, "SELECT doctors.name, hospitals.name FROM doctors JOIN hospitals ON hospital_id = id")
    assert "Dr. Amira" in out and "Clinique du Lac" in out
