# AI-CITY


## Setup

1. Clone the repository:
   ```
   git clone https://github.com/VedantPancholi/AI-CITY.git
   cd AI-CITY
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

5. Create a `config.json` file in the project root with your Groq API key:
   ```json
   {
     "GROQ_API_KEY": "your-api-key-here",
     "LLMWHISPERER_API_KEY": "Generate LLM Whisper API Key"
   }
   ```

## Running the Application

1. Ensure your virtual environment is activated.

2. Run the Streamlit app:
   ```
   streamlit run app2.py
   ```

3. Open your web browser and navigate to the URL provided by Streamlit (usually http://localhost:8501).

