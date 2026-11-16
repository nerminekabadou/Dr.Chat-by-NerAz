# Self-contained demo image (FastAPI backend + Streamlit UI, fictional data).
# Listens on $PORT (default 7860).
FROM python:3.12-slim

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .
RUN python deploy/seed_demo_db.py demo/hospital.db && chmod a-w demo/hospital.db

USER user
ENV DEMO_MODE=1 \
    MAX_QUESTIONS_PER_SESSION=15 \
    CHAT_API_URL=http://127.0.0.1:8000/ask_gemini \
    DATABASE_URL="sqlite:///file:/home/user/app/demo/hospital.db?mode=ro&uri=true"

EXPOSE 7860
CMD ["sh", "deploy/start.sh"]
