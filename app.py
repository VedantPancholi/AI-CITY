import PyPDF2
import streamlit as st
from groq import Groq
import os
import json
import re
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pdfplumber
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import docx
import io

# Streamlit page configuration
st.set_page_config(
    page_title="Financial Data Extractor",
    page_icon="📊",
    layout="centered"
)

st.title("📊 Financial Data Extractor")

# Load environment variables
load_dotenv()
working_dir = os.path.dirname(os.path.abspath(__file__))
config_data = json.load(open(f"{working_dir}/config.json"))
os.environ["GROQ_API_KEY"] = config_data["GROQ_API_KEY"]

# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

def extract_text_from_pdf(file):
    """Extracts text from PDF with improved formatting and layout handling."""
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text(layout=True) or ""
                text += "\n\n"
                
                # Extract tables and append as text
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        text += " | ".join(str(cell) for cell in row if cell) + "\n"
                text += "\n"

        if not text.strip():
            raise ValueError("No text extracted. Trying alternative method.")
    except Exception as e:
        st.warning(f"PDF extraction issue: {e}. Using fallback.")
        try:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            st.error(f"Final text extraction failed: {e}")
            return ""
    
    return clean_extracted_text(text)

def clean_extracted_text(text):
    """Cleans extracted financial text by fixing number formatting and common OCR issues."""
    if not text:
        return ""

    # Standardize currency formats
    text = text.replace('Rs ', 'Rs. ').replace('₹', 'Rs.')
    text = re.sub(r'(?<=\d),(?=\d{3})', '', text)  # Fix thousands separator
    text = re.sub(r'(?i)crores?', 'cr', text)  # Normalize "crores"
    text = re.sub(r'(?i)lakhs?', 'lakh', text)  # Normalize "lakhs"

    # Standardize quarter representation
    text = re.sub(r'Q(\d)\s+FY', r'Q\1FY', text)
    text = re.sub(r'(?i)quarter\s+(\d)', r'Q\1', text)

    return text.strip()

def standardize_financial_terms(terms):
    """Maps financial terms to standard formats for easier searching."""
    term_mapping = {
        "revenue": ["revenue", "total revenue", "net revenue", "turnover"],
        "pat": ["pat", "profit after tax", "net profit", "net earnings"],
        "ebitda": ["ebitda", "operating profit", "earnings before interest, tax, depreciation"],
        "eps": ["eps", "earnings per share", "basic eps", "diluted eps"],
        "dividend": ["dividend", "dividends declared", "dividend payout"],
    }

    standardized_terms = []
    for term in terms:
        term_lower = term.lower().strip()
        for key, variations in term_mapping.items():
            if term_lower in variations:
                standardized_terms.append(key.upper())
                break
        else:
            standardized_terms.append(term.upper())
    
    return standardized_terms

def find_quarter_positions(text, quarter, year):
    """Finds positions of quarter and fiscal year references in extracted text."""
    fiscal_year = str(year)[2:]  # Extract last 2 digits (e.g., 2025 → '25')

    quarter_patterns = [
        rf"{quarter}FY{fiscal_year}",
        rf"{quarter} FY{fiscal_year}",
        rf"{quarter.lower()}fy{fiscal_year}",
        rf"quarter ended (june|september|december|march) {year}",
        rf"{quarter} {year}",
    ]

    positions = []
    for pattern in quarter_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        positions.extend([m.start() for m in matches])

    return positions

def extract_llm_response(text, terms, quarter, year):
    """Uses LLM to extract financial values explicitly for the requested quarter and year."""
    positions = find_quarter_positions(text, quarter, year)
    
    if not positions:
        st.warning(f"No exact match for {quarter}FY{year} found in document.")
        return {}

    start = max(0, positions[0] - 2000)
    end = min(len(text), positions[0] + 2000)
    truncated_text = text[start:end]

    prompt = f"""
    Extract ONLY financial values explicitly labeled for {quarter}FY{str(year)[2:]}.

    - Quarter: {quarter}
    - Year: FY{str(year)[2:]}
    - Terms: {', '.join(terms)}
    - DO NOT return values from other quarters, YTD figures, or cumulative values.
    - If term not found, return "Not found".

    Example response:
    {{
        "Revenue": "Rs. 100 cr",
        "PAT": "Rs. 50 cr"
    }}

    Text context:
    {truncated_text}
    """

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a financial data extraction tool. Extract ONLY the requested values."},
                {"role": "user", "content": prompt}
            ],
            model="mixtral-8x7b-32768",
            temperature=0,
            max_tokens=500
        )

        response_text = completion.choices[0].message.content.strip()
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {}

    except Exception as e:
        st.error(f"LLM extraction failed: {e}")
        return {}

def main():
    st.title("Financial Data Analyzer")

    uploaded_file = st.file_uploader("Upload a financial report (PDF)", type=['pdf'])
    
    if uploaded_file:
        with st.spinner("Extracting text..."):
            text = extract_text_from_pdf(uploaded_file)

        display_text = st.expander("View Extracted Text")
        display_text.text(text[:5000])  # Show first 5000 characters

        terms = st.text_input("Enter financial terms (comma-separated)", "Revenue, PAT, EBITDA").split(',')
        terms = [term.strip() for term in terms]
        
        quarter = st.selectbox("Select Quarter", ["Q1", "Q2", "Q3", "Q4"])
        year = st.number_input("Enter Fiscal Year", min_value=2000, max_value=2100, value=2025)

        if st.button("Analyze"):
            terms = standardize_financial_terms(terms)
            results = extract_llm_response(text, terms, quarter, year)

            if results:
                df = pd.DataFrame(list(results.items()), columns=['Term', 'Value'])
                st.table(df)
            else:
                st.warning("No relevant data found.")

if __name__ == "__main__":
    main()
