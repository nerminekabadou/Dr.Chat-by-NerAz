from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama
import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI()

# Instantiate the Llama model
# Load Llama model path from .env
LLAMA_MODEL_PATH = os.getenv("LLAMA_MODEL_PATH")
try:
    my_awesome_llama_model = Llama(model_path=LLAMA_MODEL_PATH)
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

class Query(BaseModel):
    question: str

def generate_text_from_prompt(user_prompt, max_tokens=50, temperature=0.3, top_p=0.9, echo=False):
    try:
        model_output = my_awesome_llama_model(
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            echo=echo,
        )
        return model_output
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

def extract_first_sentence(text):
    sentences = text.split('.')
    return sentences[0].strip() + '.' if sentences else text

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Llama and Gemini API. Use the /ask endpoint for Llama and /ask_gemini for Gemini."}

@app.post("/ask")
async def ask_question(query: Query):
    if not query.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    prompt = f"Provide a single-paragraph response and give a good description: {query.question}"
    try:
        llama_model_response = generate_text_from_prompt(prompt)
        raw_result = llama_model_response["choices"][0]["text"].strip()
        final_result = extract_first_sentence(raw_result)
        return {"response": raw_result} 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.post("/ask_gemini")
async def ask_gemini(query: Query):
    if not query.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        response = gemini_model.generate_content(query.question)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question with Gemini: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)