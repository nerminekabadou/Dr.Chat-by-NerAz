# Dr.Chat: AI assistant for a hospital management platform

[![tests](https://github.com/nerminekabadou/Dr.Chat-by-NerAz/actions/workflows/tests.yml/badge.svg)](https://github.com/nerminekabadou/Dr.Chat-by-NerAz/actions/workflows/tests.yml)

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

Each question takes **two LLM calls**: one decides whether data is needed and, if so, writes the SQL in one go; the other turns the query result into an answer. The prompts are LangChain chains (`prompt | llm | parser`). They call the FastAPI backend through a custom LangChain `LLM` wrapper, or Gemini directly when `LLM_MODE=direct` (used by the hosted demo). The backend serves Google Gemini (`/ask_gemini`) and, optionally, a local Llama model through `llama-cpp-python` (`/ask`). The Gemini model is picked at runtime: `GEMINI_MODEL` if it's available, otherwise the newest stable Flash model your key can use, because Google retires model versions.

### Safety of LLM-generated SQL
The LLM writes the SQL, so the app treats it as untrusted input:

1. [`sql_guard.py`](sql_guard.py) only accepts a single `SELECT` (or `WITH … SELECT`) statement. It rejects multiple statements and any write or DDL keyword.
2. The database connection itself is opened with `default_transaction_read_only=on`, so a query that slipped past the guard still couldn't change any data.
3. Only the tables the chatbot needs are exposed to the model: `doctors`, `hospitals`, `illnesses`, `medications`.

For production you should also connect with a database user that only has `SELECT` rights.

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
app.py          Streamlit chat UI, routing and text-to-SQL chains
main.py         FastAPI backend (Gemini + optional Llama)
sql_guard.py    Validation of generated SQL
tests/          Unit tests
```

## Author
Nermine Kabadou ([@nerminekabadou](https://github.com/nerminekabadou))
