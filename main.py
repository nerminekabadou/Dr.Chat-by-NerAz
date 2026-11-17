"""FastAPI backend exposing the language models used by Dr.Chat.

* ``POST /ask_gemini`` - Google Gemini (used by the Streamlit app).
* ``POST /ask``        - optional local Llama model (llama-cpp-python), loaded
  on first use so the API starts even when no local model is installed.
"""

import os
from functools import lru_cache

import google.generativeai as genai
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from llm_models import generate_text

load_dotenv()

app = FastAPI(title="Dr.Chat API")


class Query(BaseModel):
    question: str = Field(min_length=1)


@lru_cache(maxsize=1)
def get_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    genai.configure(api_key=api_key)
    return genai


@lru_cache(maxsize=1)
def get_llama():
    model_path = os.getenv("LLAMA_MODEL_PATH")
    if not model_path:
        raise HTTPException(status_code=503, detail="LLAMA_MODEL_PATH is not configured")
    try:
        from llama_cpp import Llama  # optional dependency, see requirements-llama.txt
    except ImportError as error:
        raise HTTPException(status_code=503, detail="llama-cpp-python is not installed") from error
    return Llama(model_path=model_path, verbose=False)


@app.get("/")
async def read_root():
    return {"message": "Dr.Chat API. Use POST /ask_gemini (Gemini) or POST /ask (local Llama)."}


@app.post("/ask")
def ask_llama(query: Query):
    llama = get_llama()
    prompt = f"Provide a single-paragraph response and give a good description: {query.question}"
    try:
        output = llama(prompt, max_tokens=256, temperature=0.3, top_p=0.9)
        return {"response": output["choices"][0]["text"].strip()}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Llama error: {error}") from error


@app.post("/ask_gemini")
def ask_gemini(query: Query):
    client = get_gemini()
    try:
        return {"response": generate_text(client, query.question)}
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Gemini error: {error}") from error


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
