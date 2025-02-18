import streamlit as st
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.utilities import SQLDatabase
from langchain.llms.base import LLM
import requests
import re 
from typing import Any, List, Mapping, Optional
from dotenv import load_dotenv
import os

class CustomLLM(LLM):
    api_url: str = "http://localhost:8000/ask_gemini"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        response = requests.post(self.api_url, json={"question": prompt})
        if response.status_code == 200:
            return response.json()["response"]
        else:
            raise Exception(f"API request failed with status code {response.status_code}")

    @property
    def _llm_type(self) -> str:
        return "custom_llama_api"

st.set_page_config(page_title="Dr.Chat by NerAz", page_icon=":hospital:")
st.title("Dr.Chat by NerAz")

# Load environment variables
load_dotenv()
# Initialize custom LLM
llm = CustomLLM()

# Database connection
host = os.getenv("DATABASE_HOST")
port = os.getenv("DATABASE_PORT")
username = os.getenv("DATABASE_USER")
password = os.getenv("DATABASE_PASSWORD")
database_schema = os.getenv("DATABASE_SCHEMA")
postgres_uri = f"postgresql://{username}:{password}@{host}:{port}/{database_schema}"

#include the tables you need
db = SQLDatabase.from_uri(postgres_uri, include_tables=['doctors', 'hospitals', 'illnesses','medications'], sample_rows_in_table_info=2)

# Create prompt templates and chains
question_type_prompt = PromptTemplate.from_template(
    """Determine if the following question requires a database query or a general answer.
    Question: {question}
    If it requires a database query, respond with 'DATABASE'. If it's a general question, respond with 'GENERAL'.
    Response (DATABASE/GENERAL): """)

question_type_chain = LLMChain(llm=llm, prompt=question_type_prompt)

sql_prompt = PromptTemplate.from_template(
    """Given the following SQL table information, write a SQL query to answer the user's question. 
    The query should be valid PostgreSQL syntax.
    SQL table info: {table_info}
    User question: {input}
    Provide only the SQL query, without any additional text or explanation.
    SQL query: """)

sql_chain = LLMChain(llm=llm, prompt=sql_prompt)

response_prompt = PromptTemplate.from_template(
    """Based on the following information, provide a natural language response to the user's question. Describe in a detailed human readable format and say thank you.    User question: {question}
    Context: {context}
    Your response: """)

response_chain = LLMChain(llm=llm, prompt=response_prompt)

def process_user_input(user_input):
    # Determine question type
    question_type = question_type_chain.run(question=user_input).strip().upper()

    if question_type == 'DATABASE':
        # Generate SQL query
        sql_response = sql_chain.run(input=user_input, table_info=db.get_table_info())
        print("Generated SQL query:", sql_response)
        # Clean up the SQL query
        cleaned_sql_query = ' '.join(sql_response.replace('```sql', '').replace('```', '').strip().split())
        print("Cleaned SQL query:", cleaned_sql_query)

        # Execute the query
        try:
            result = db.run(cleaned_sql_query)
            context = f"SQL Query: {cleaned_sql_query}\nQuery Result: {result}"
        except Exception as e:
            context = f"Error executing SQL query: {str(e)}"
    else:
        # General question
        context = "This is a general question that doesn't require database access."

    # Generate the final response
    final_response = response_chain.run(question=user_input, context=context)
    return final_response

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What would you like to know about us?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate a response
    with st.spinner("Thinking..."):
        response = process_user_input(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    