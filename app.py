"""Streamlit chat interface for Dr.Chat.

Each question is routed by the LLM to one of two paths:
  * DATABASE - the LLM writes a SQL query, which is validated and run
    against the hospital database, then the result is turned into an answer;
  * GENERAL  - the LLM answers directly.
"""

import os
from typing import Any, List, Optional

import requests
import streamlit as st
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.language_models.llms import LLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from sql_guard import UnsafeQueryError, validate_select

load_dotenv()

API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/ask_gemini")
TABLES = ["doctors", "hospitals", "illnesses", "medications"]


class BackendLLM(LLM):
    """LangChain wrapper around the FastAPI backend defined in ``main.py``."""

    api_url: str = API_URL
    timeout: int = 60

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        response = requests.post(self.api_url, json={"question": prompt}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()["response"]

    @property
    def _llm_type(self) -> str:
        return "dr_chat_backend"


@st.cache_resource
def get_database() -> SQLDatabase:
    uri = "postgresql://{user}:{password}@{host}:{port}/{name}".format(
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD"),
        host=os.getenv("DATABASE_HOST"),
        port=os.getenv("DATABASE_PORT", "5432"),
        name=os.getenv("DATABASE_SCHEMA"),
    )
    # Every transaction is read-only at the PostgreSQL level: even a query that
    # slipped past sql_guard could not modify data.
    return SQLDatabase.from_uri(
        uri,
        include_tables=TABLES,
        sample_rows_in_table_info=2,
        engine_args={"connect_args": {"options": "-c default_transaction_read_only=on"}},
    )


llm = BackendLLM()
parser = StrOutputParser()

route_chain = PromptTemplate.from_template(
    """Determine if the following question requires a database query or a general answer.
Question: {question}
If it requires a database query, respond with 'DATABASE'. If it's a general question, respond with 'GENERAL'.
Response (DATABASE/GENERAL): """
) | llm | parser

sql_chain = PromptTemplate.from_template(
    """Given the following SQL table information, write a single read-only PostgreSQL
SELECT query that answers the user's question.
SQL table info: {table_info}
User question: {question}
Provide only the SQL query, without any additional text or explanation.
SQL query: """
) | llm | parser

answer_chain = PromptTemplate.from_template(
    """Based on the following information, answer the user's question in a clear,
detailed and human-readable way.
User question: {question}
Context: {context}
Your response: """
) | llm | parser


def build_context(question: str) -> str:
    route = route_chain.invoke({"question": question}).strip().upper()
    if "DATABASE" not in route:
        return "This is a general question that doesn't require database access."

    db = get_database()
    generated = sql_chain.invoke({"question": question, "table_info": db.get_table_info()})
    try:
        query = validate_select(generated)
    except UnsafeQueryError as error:
        return f"The generated query was rejected for safety reasons: {error}"

    try:
        result = db.run(query)
    except Exception as error:  # surfaced to the LLM so it can explain the failure
        return f"Error executing SQL query: {error}"
    return f"SQL Query: {query}\nQuery Result: {result}"


def answer(question: str) -> str:
    return answer_chain.invoke({"question": question, "context": build_context(question)})


st.set_page_config(page_title="Dr.Chat by NerAz", page_icon=":hospital:")
st.title("Dr.Chat by NerAz")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What would you like to know about us?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        try:
            response = answer(prompt)
        except requests.RequestException as error:
            response = f"Sorry, the assistant is unavailable right now ({error})."

    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
