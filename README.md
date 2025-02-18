# AI-Powered Chatbot for Hospital Management Platform

## Project Overview
The healthcare sector faces multiple challenges, including efficient resource management and improving service quality. To address these issues, an AI-powered chatbot has been developed and integrated into a hospital management platform. This chatbot enhances communication and facilitates access to information within hospitals through artificial intelligence.

The project focuses on designing an advanced chatbot specifically for the hospital management platform. Leveraging state-of-the-art AI technologies, the chatbot is capable of handling two types of queries:

### Features
* **General Questions**  
  Provides detailed and informative answers on various topics related to healthcare and beyond, with fine-tuning of the model to enhance its accuracy for these types of queries.
* **Specific Questions**  
  Accesses the platform's database to deliver personalized responses, such as doctor availability, hospital capacities, or medication information, ensuring real-time updates based on user prompts.

---

## Installation Instructions

### Prerequisites
Before running the project, ensure you have the following installed:
- **Python 3.7+**  
  You can download Python from [here](https://www.python.org/downloads/).
- **pip**  
  Make sure pip (Python's package installer) is installed by running:
  ```bash
  python -m ensurepip --upgrade
  ```

### Step 1: Clone the Repository
First, clone the repository to your local machine:
```bash
git clone [<repository-url>](https://github.com/nerminekabadou/Dr.Chat-by-NerAz)
cd Dr.Chat-by-NerAz
```

### Step 2: Create and Activate a Virtual Environment (Recommended)
It is recommended to create a virtual environment to keep dependencies isolated:
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install the Dependencies
Run the following command to install all the required dependencies:
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables
The project relies on environment variables for certain configurations. Create a `.env` file in the root directory of the project and add the following variables:
```ini
DATABASE_HOST=your_database_host
DATABASE_PORT=your_database_port
DATABASE_USER=your_database_user
DATABASE_PASSWORD=your_database_password
DATABASE_SCHEMA=your_database_schema
LLAMA_MODEL_PATH=path_to_your_llama_model
GEMINI_API_KEY=your_gemini_api_key
```

### Step 5: Run the FastAPI Server
To run the FastAPI backend, use the following command:
```bash
uvicorn main:app --reload 
```

This will start the server on `http://localhost:8000`. You can access the API through this endpoint.

### Step 6: Run the Streamlit App
To run the frontend Streamlit application, use the following command:
```bash
streamlit run main.py
```

This will start the Streamlit app, and you can access the chatbot interface at `http://localhost:8501` in your browser.

## Usage

### 1. Interacting with the Chatbot
Once the application is running, the chatbot interface will appear in your browser. You can start interacting with the chatbot by typing your queries. The chatbot will respond with information either from the database (for specific queries) or from the general model (for general questions).

### 2. Available Endpoints
The FastAPI server provides the following endpoints:
* **GET /** Returns a welcome message.
* **POST /ask** Accepts a query and processes it using the Llama model. Example:
  ```json
  {
    "question": "What are the available medications?"
  }
  ```
* **POST /ask_gemini** Accepts a query and processes it using the Gemini model. Example:
  ```json
  {
    "question": "What is the doctor's availability?"
  }
  ```

## Additional Notes
* Ensure that you have access to the necessary databases and models to run the application successfully.
* The chatbot's responses may vary depending on the specific training and tuning of the AI models used.
