import pytest
from langchain_community.utilities import SQLDatabase

import pipeline
from deploy.seed_demo_db import main as seed


class FakePlan:
    """Stands in for the LLM planning chain: always returns the same reply."""

    def __init__(self, reply):
        self.reply = reply

    def invoke(self, _inputs):
        return self.reply


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "hospital.db"
    seed(str(path))
    return SQLDatabase.from_uri(f"sqlite:///file:{path}?mode=ro&uri=true",
                                include_tables=["doctors", "hospitals", "illnesses", "medications"])


def test_database_question_runs_the_validated_query(db):
    sql = "SELECT d.name, h.name FROM doctors d JOIN hospitals h ON d.hospital_id = h.id " \
          "WHERE d.specialty = 'Cardiology'"
    context, trace = pipeline.build_context(FakePlan(sql), db, "Which cardiologists?")
    assert trace["route"] == "DATABASE" and trace["guard"] == "passed"
    assert "Dr. Amira Ben Salah" in context and "Hôpital Central de Tunis" in context


def test_general_question_skips_the_database(db):
    context, trace = pipeline.build_context(FakePlan("GENERAL"), db, "What is a migraine?")
    assert trace == {"route": "GENERAL", "sql": None, "guard": None}


@pytest.mark.parametrize("reply", [
    "SELECT 1; DELETE FROM doctors",
    "SELECT name FROM sqlite_master",
    "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT count(*) FROM r",
])
def test_malicious_sql_is_blocked_before_reaching_the_database(db, reply):
    context, trace = pipeline.build_context(FakePlan(reply), db, "attack")
    assert trace["guard"].startswith("blocked")
    assert "rejected for safety reasons" in context
