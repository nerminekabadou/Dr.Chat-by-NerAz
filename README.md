# Dr.Chat: AI assistant for a hospital management platform

[![tests](https://github.com/nerminekabadou/Dr.Chat-by-NerAz/actions/workflows/tests.yml/badge.svg)](https://github.com/nerminekabadou/Dr.Chat-by-NerAz/actions/workflows/tests.yml)

**[▶ Try it live](https://dr-chat-nermine.streamlit.app/)**: it runs on a database of fictional hospitals, and each answer shows the SQL the LLM wrote and the safety guard's verdict. *The free hosting sleeps when idle, so the first visit can take about a minute. On the free Gemini tier, questions are rate-limited.*

<img src="docs/demo.png" width="640" alt="Dr.Chat answering which doctors work in cardiology, showing the generated SQL and the safety guard verdict">

Dr.Chat is a chatbot for a hospital management platform. It answers two kinds of questions:

- **General questions** about health or the hospital, answered directly by an LLM.
- **Questions about the platform's data**, such as doctors, hospitals, illnesses and medications. The LLM turns the question into SQL, the query runs against the hospital's PostgreSQL database, and the result is rewritten as a natural-language answer.

## How it works

```
 Streamlit UI (app.py)
   │ 1. plan: SELECT query, or GENERAL  ┌──────────────────────────┐
   │                            ───────▶│ FastAPI backend (main.py)│──▶ Gemini / local Llama
   │ 2. answer from the SQL result ◀────└──────────────────────────┘
   │
   └─ validated SELECT ──▶ PostgreSQL or SQLite (read-only connection)
```

Each question takes **two LLM calls**: one decides whether data is needed and, if so, writes the SQL in one go; the other turns the query result into an answer. The prompts are LangChain chains (`prompt | llm | parser`). They call the FastAPI backend through a custom LangChain `LLM` wrapper, or Gemini directly when `LLM_MODE=direct` (used by the hosted demo). The backend serves Google Gemini (`/ask_gemini`) and, optionally, a local Llama model through `llama-cpp-python` (`/ask`). The Gemini model is picked at runtime, because Google retires model versions and new keys lose access to older ones. The app tries `GEMINI_MODEL` (if set), then Google's `gemini-flash-latest` aliases, then the newest Flash models on your account, and remembers the first one that answers ([`llm_models.py`](llm_models.py)).

### Safety of LLM-generated SQL
The LLM writes the SQL, so the app treats it as untrusted input and defends in layers:

1. **Parser-based guard** ([`sql_guard.py`](sql_guard.py)): the query is parsed with sqlglot and accepted only if it is a single `SELECT` with no write, DDL or engine command anywhere in it. It may only read the allowed tables (`doctors`, `hospitals`, `illnesses`, `medications`), only call allow-listed functions, and has no recursive CTEs. A `LIMIT` is added when missing.
2. **Read-only execution** ([`query_runner.py`](query_runner.py)): read-only connection, `SET TRANSACTION READ ONLY` on every PostgreSQL query, and a 5-second time limit.
3. For production, also connect with a database user that only has `SELECT` rights on those tables.

**[Security benchmark](security/README.md):** 90 adversarial prompts on two local LLMs, plus 41 hand-written SQL attacks on SQLite and PostgreSQL. Before hardening, data leaks and denial-of-service queries got through. After hardening there are **0 successful attacks**, and accuracy on legitimate questions is unchanged. The fuzzer runs in CI on every push.

<img src="security/results/attack_llm.png" width="720" alt="Attack benchmark: harmful SQL written by the models vs harm that reached the app before and after hardening">

## Tech stack
Python · Streamlit · FastAPI · LangChain · Google Gemini · llama-cpp-python · PostgreSQL / SQLAlchemy · pytest · GitHub Actions

## Getting started

Requirements: Python 3.10+ and a PostgreSQL database containing the tables above.

```bash
git clone https://github.com/nerminekabadou/Dr.Chat-by-NerAz
cd Dr.Chat-by-NerAz
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# optional, for the local Llama endpoint:
pip install -r requirements-llama.txt

cp .env.example .env               # then fill in your values
```

Run the backend and the UI in two terminals:

```bash
uvicorn main:app --reload          # API on http://localhost:8000 (docs at /docs)
streamlit run app.py               # chat UI on http://localhost:8501
```

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/`           | Health / welcome message                     |
| POST   | `/ask_gemini` | `{"question": "..."}` → answer from Gemini   |
| POST   | `/ask`        | `{"question": "..."}` → answer from local Llama (needs `LLAMA_MODEL_PATH`) |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Project structure

```
app.py          Streamlit chat UI (demo mode, answer traces)
main.py         FastAPI backend (Gemini + optional Llama)
pipeline.py     Plan → guard → run → answer (shared by the app and the benchmark)
sql_guard.py    Validation of generated SQL (sqlglot)
query_runner.py Read-only execution with a time limit
llm_models.py   Picks an available Gemini model at runtime
security/       Text-to-SQL attack benchmark and results
deploy/         Demo database seed and Docker image
tests/          Unit tests
```

## Author
Nermine Kabadou ([@nerminekabadou](https://github.com/nerminekabadou))
