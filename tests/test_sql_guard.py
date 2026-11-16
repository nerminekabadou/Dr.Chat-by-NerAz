import pytest

from sql_guard import UnsafeQueryError, clean_sql, validate_select


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("SELECT * FROM doctors", "SELECT * FROM doctors"),
        ("```sql\nSELECT name\nFROM doctors;\n```", "SELECT name FROM doctors"),
        ("WITH d AS (SELECT * FROM doctors) SELECT * FROM d",
         "WITH d AS (SELECT * FROM doctors) SELECT * FROM d"),
        ("SELECT * FROM hospitals WHERE name = 'Drop-in; update centre'",
         "SELECT * FROM hospitals WHERE name = 'Drop-in; update centre'"),
        ("SELECT created_at, updated_at FROM doctors", "SELECT created_at, updated_at FROM doctors"),
    ],
)
def test_accepts_read_only_queries(raw, expected):
    assert validate_select(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "DELETE FROM doctors",
        "DROP TABLE doctors",
        "UPDATE doctors SET name = 'x'",
        "SELECT 1; DROP TABLE doctors",
        "SELECT * INTO backup FROM doctors",
        "WITH x AS (DELETE FROM doctors RETURNING *) SELECT * FROM x",
        "SELECT 1 -- harmless\n; TRUNCATE doctors",
    ],
)
def test_rejects_anything_else(raw):
    with pytest.raises(UnsafeQueryError):
        validate_select(raw)


def test_clean_sql_removes_comments():
    assert clean_sql("SELECT 1 /* note */ -- end") == "SELECT 1"
