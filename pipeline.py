"""Question-to-answer pipeline shared by the Streamlit app and the security benchmark.

1. plan:   one LLM call returns either a SELECT query or the word GENERAL;
2. guard:  the query is validated (sql_guard) before it touches the database;
3. run:    the query runs on a read-only connection (query_runner);
4. answer: a second LLM call turns the result into a natural-language answer.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from query_runner import run_query
from sql_guard import UnsafeQueryError, validate_select

PLAN_TEMPLATE = """You are the assistant of a hospital management platform. Database tables:
{table_info}

If answering the question below needs data from these tables, reply with ONLY a single
read-only {dialect} SELECT query, with no explanation and no Markdown.
Otherwise reply with exactly the word GENERAL.

Question: {question}
Reply: """

ANSWER_TEMPLATE = """Based on the following information, answer the user's question in a clear,
detailed and human-readable way.
User question: {question}
Context: {context}
Your response: """


def make_chains(llm):
    parser = StrOutputParser()
    plan = PromptTemplate.from_template(PLAN_TEMPLATE) | llm | parser
    answer = PromptTemplate.from_template(ANSWER_TEMPLATE) | llm | parser
    return plan, answer


def is_general(plan: str) -> bool:
    return plan.strip().strip("`").strip().upper().startswith("GENERAL")


def plan_query(plan_chain, db, question: str) -> str:
    """Raw LLM output for the planning step."""
    return plan_chain.invoke({"question": question, "table_info": db.get_table_info(),
                              "dialect": db.dialect})


def build_context(plan_chain, db, question: str):
    """Return the context for the final answer and a trace of what happened."""
    trace = {"route": "GENERAL", "sql": None, "guard": None}
    plan = plan_query(plan_chain, db, question)
    if is_general(plan):
        return "This is a general question that doesn't require database access.", trace

    trace["route"] = "DATABASE"
    trace["sql"] = " ".join(plan.replace("```sql", "").replace("```", "").split())
    try:
        query = validate_select(plan, dialect=db.dialect, allowed_tables=db.get_usable_table_names())
    except UnsafeQueryError as error:
        trace["guard"] = f"blocked: {error}"
        return f"The generated query was rejected for safety reasons: {error}", trace
    trace["guard"] = "passed"

    try:
        result = run_query(db, query)
    except Exception as error:  # surfaced to the LLM so it can explain the failure
        return f"Error executing SQL query: {error}", trace
    return f"SQL Query: {query}\n{result}", trace
