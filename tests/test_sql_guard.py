import pytest

from sql_guard import DEFAULT_LIMIT, UnsafeQueryError, clean_sql, validate_select


@pytest.mark.parametrize("raw", [
    "SELECT * FROM doctors",
    "```sql\nSELECT name\nFROM doctors;\n```",
    "WITH d AS (SELECT * FROM doctors) SELECT * FROM d",
    "SELECT * FROM hospitals WHERE name = 'Drop-in; update centre'",
    "SELECT d.name, h.name FROM doctors d JOIN hospitals h ON d.hospital_id = h.id",
    "SELECT name FROM doctors UNION SELECT name FROM hospitals",
    "SELECT strftime('%Y', 'now'), count(*) FROM doctors",
])
def test_accepts_read_only_queries_on_allowed_tables(raw):
    assert validate_select(raw).upper().startswith(("SELECT", "WITH"))


def test_adds_a_limit_when_missing():
    assert validate_select("SELECT name FROM doctors").endswith(f"LIMIT {DEFAULT_LIMIT}")
    assert validate_select("SELECT name FROM doctors LIMIT 3").endswith("LIMIT 3")


@pytest.mark.parametrize("raw, reason", [
    ("", "did not return"),
    ("SELECT 'unterminated FROM doctors", "could not be parsed"),
    ("Sure! Here is the table:\n CREATE TABLE x (a TEXT, \n PRIMAR", "could not be parsed|Only SELECT"),
    ("DELETE FROM doctors", "Only SELECT"),
    ("SELECT 1; DROP TABLE doctors", "single statement"),
    ("SELECT * INTO backup FROM doctors", "Into"),
    ("SELECT name FROM staff_salaries", "not available"),
    ("SELECT name, sql FROM sqlite_master", "not available"),
    ("SELECT name FROM pragma_table_info('doctors')", "not allowed"),
    ("SELECT length(randomblob(1000000000))", "randomblob"),
    ("SELECT load_extension('/tmp/x.so')", "load_extension"),
    ("WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT count(*) FROM r",
     "Recursive"),
    ("SELECT count(*) FROM doctors a, doctors b, doctors c, doctors d, doctors e", "At most"),
    ("PRAGMA query_only = 0", "Only SELECT"),
])
def test_rejects_unsafe_sqlite_queries(raw, reason):
    with pytest.raises(UnsafeQueryError, match=reason):
        validate_select(raw)


@pytest.mark.parametrize("raw, reason", [
    ("WITH x AS (DELETE FROM doctors RETURNING *) SELECT * FROM x", "Delete"),
    ("SELECT set_config('default_transaction_read_only', 'off', false)", "set_config"),
    ("SELECT pg_sleep(600)", "pg_sleep"),
    ("SELECT usename FROM pg_user", "not available"),
    ("SELECT table_name FROM information_schema.tables", "Schema-qualified"),
    ("SELECT count(*) FROM generate_series(1, 1000000)", "not allowed"),
])
def test_rejects_unsafe_postgres_queries(raw, reason):
    with pytest.raises(UnsafeQueryError, match=reason):
        validate_select(raw, dialect="postgresql")


def test_custom_allow_list():
    assert validate_select("SELECT * FROM staff_salaries", allowed_tables={"staff_salaries"})


def test_clean_sql_removes_fences():
    assert clean_sql("```sqlite\nSELECT 1;\n```") == "SELECT 1"
