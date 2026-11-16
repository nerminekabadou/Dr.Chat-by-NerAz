#!/bin/sh
# FastAPI backend (internal) + Streamlit UI (public port $PORT, default 7860).
uvicorn main:app --host 127.0.0.1 --port 8000 &
exec streamlit run app.py --server.port "${PORT:-7860}" --server.address 0.0.0.0 --server.headless true
