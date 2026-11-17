"""Part 1 of the security benchmark: fuzz the SQL guard with malicious SQL.

Every payload in payloads.MALICIOUS is run through two configurations:
  before - the original regex guard, no query time limit;
  after  - the parser-based guard (sql_guard.py) and the 5 s time limit.
When the guard lets a query through, it is executed exactly like the app
would: on a read-only connection, through query_runner.run_query.
Outcomes:
  guard    - rejected by the guard
  database - the database refused it (read-only, permissions, ...)
  timeout  - stopped by the query time limit
  SUCCEEDED - the attack achieved its goal

Usage (PostgreSQL is optional):
  python -m security.fuzz_guard [--postgres postgresql://user:pass@host/db]
"""

import argparse
import json
import os
import sqlite3
import tempfile
import time

from langchain_community.utilities import SQLDatabase
from sqlalchemy import text

import query_runner
import sql_guard
from deploy.seed_demo_db import DOCTORS, HOSPITALS, ILLNESSES, MEDICATIONS
from deploy.seed_demo_db import main as seed_sqlite
from security import legacy_guard
from security.payloads import BENIGN, MALICIOUS

HARNESS_LIMIT_S = 20  # anything still running after this counts as a successful DoS
CONFIGS = {"before": (legacy_guard, None), "after": (sql_guard, query_runner.DEFAULT_TIMEOUT_S)}
SALARIES = [(1, "Dr. Amira Ben Salah", 9800), (2, "Dr. Karim Trabelsi", 9100)]


def sqlite_target():
    path = os.path.join(tempfile.mkdtemp(), "bench.db")
    seed_sqlite(path)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE staff_salaries (id INTEGER, name TEXT, monthly_salary INTEGER)")
    con.executemany("INSERT INTO staff_salaries VALUES (?,?,?)", SALARIES)
    con.commit()
    con.close()
    return SQLDatabase.from_uri(f"sqlite:///file:{path}?mode=ro&uri=true",
                                include_tables=["doctors", "hospitals", "illnesses", "medications"])


def postgres_target(url):
    admin = SQLDatabase.from_uri(url)
    with admin._engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS doctors, hospitals, illnesses, medications, "
                       "staff_salaries, doctors_copy CASCADE"))
        c.execute(text("CREATE TABLE hospitals (id INT PRIMARY KEY, name TEXT, city TEXT, "
                       "total_beds INT, available_beds INT)"))
        c.execute(text("CREATE TABLE doctors (id INT PRIMARY KEY, name TEXT, specialty TEXT, "
                       "hospital_id INT, available_days TEXT)"))
        c.execute(text("CREATE TABLE illnesses (id INT PRIMARY KEY, name TEXT, description TEXT, specialty TEXT)"))
        c.execute(text("CREATE TABLE medications (id INT PRIMARY KEY, name TEXT, illness_id INT, "
                       "dosage TEXT, units_in_stock INT)"))
        c.execute(text("CREATE TABLE staff_salaries (id INT, name TEXT, monthly_salary INT)"))
        for table, rows in [("hospitals", HOSPITALS), ("doctors", DOCTORS), ("illnesses", ILLNESSES),
                            ("medications", MEDICATIONS), ("staff_salaries", SALARIES)]:
            marks = ", ".join(f":p{i}" for i in range(len(rows[0])))
            c.execute(text(f"INSERT INTO {table} VALUES ({marks})"),
                      [{f"p{i}": v for i, v in enumerate(r)} for r in rows])
    # Same connection settings as the app (see app.get_database).
    return SQLDatabase.from_uri(
        url, include_tables=["doctors", "hospitals", "illnesses", "medications"],
        engine_args={"connect_args": {"options": "-c default_transaction_read_only=on"},
                     "pool_size": 1, "max_overflow": 0})


def guard_verdict(guard, sql, dialect):
    try:
        try:
            return "allowed", guard.validate_select(sql, dialect=dialect)
        except TypeError:  # the legacy guard has no dialect parameter
            return "allowed", guard.validate_select(sql)
    except guard.UnsafeQueryError as error:
        return "blocked", str(error)


def execute(db, sql, payload):
    """Run like the app does and classify the outcome."""
    app_limit = query_runner.DEFAULT_TIMEOUT_S
    started = time.time()
    try:
        # The app's own limit if it has one; otherwise the benchmark kills the query.
        result = query_runner.run_query(db, sql, timeout_s=app_limit or HARNESS_LIMIT_S)
    except query_runner.QueryTimeout:
        if not app_limit:
            return "SUCCEEDED", f"still running after {HARNESS_LIMIT_S}s (no time limit in the app)"
        return "timeout", f"stopped after {time.time() - started:.0f}s by the {app_limit}s limit"
    except Exception as error:
        return "database", type(error).__name__ + ": " + str(error).splitlines()[0][:120]

    if payload["id"] == "D1":  # did it really turn read-only off for the next query?
        state = query_runner.run_query(db, "SHOW default_transaction_read_only")
        if "off" in state:
            return "SUCCEEDED", "read-only mode is now OFF on the pooled connection"
        return "database", "setting was reverted when the transaction rolled back"
    if payload["category"] == "data-leak" and "Rows: []" in result:
        return "database", "no rows returned"
    return "SUCCEEDED", result.replace("\n", " ")[:120]


def run(targets):
    report = {"malicious": [], "benign": {}}
    for payload in MALICIOUS:
        for dialect, db in targets.items():
            if payload["dialects"] not in ("both", dialect):
                continue
            row = {k: payload[k] for k in ("id", "category", "harm", "sql")}
            row["dialect"] = dialect
            for name, (guard, time_limit) in CONFIGS.items():
                query_runner.DEFAULT_TIMEOUT_S = time_limit
                verdict, detail = guard_verdict(guard, payload["sql"], dialect)
                if verdict == "blocked":
                    row[name] = {"outcome": "guard", "detail": detail}
                else:
                    outcome, info = execute(db, detail, payload)
                    row[name] = {"outcome": outcome, "detail": info}
            report["malicious"].append(row)
            print(f"{row['id']:4} {dialect:8} before={row['before']['outcome']:9} "
                  f"after={row['after']['outcome']:9} {payload['harm']}", flush=True)

    for name, (guard, _) in CONFIGS.items():
        rejected = []
        for sql in BENIGN:
            for dialect in targets:
                if guard_verdict(guard, sql, dialect)[0] == "blocked":
                    rejected.append(sql)
        report["benign"][name] = {"total": len(BENIGN), "wrongly_blocked": sorted(set(rejected))}
        print(f"benign queries wrongly blocked ({name}): {len(set(rejected))}/{len(BENIGN)}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres", help="URL of a scratch PostgreSQL database (it will be overwritten)")
    parser.add_argument("--out", default="security/results/guard_fuzz.json")
    parser.add_argument("--check", action="store_true",
                        help="exit with an error if any attack succeeds or any benign query is blocked "
                             "in the hardened configuration (used in CI)")
    args = parser.parse_args()
    targets = {"sqlite": sqlite_target()}
    if args.postgres:
        targets["postgres"] = postgres_target(args.postgres)
    report = run(targets)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    if args.check:
        succeeded = [r["id"] for r in report["malicious"] if r["after"]["outcome"] == "SUCCEEDED"]
        blocked = report["benign"]["after"]["wrongly_blocked"]
        if succeeded or blocked:
            raise SystemExit(f"security regression: attacks succeeded {succeeded}, benign blocked {blocked}")
        print("security check passed")


if __name__ == "__main__":
    main()
