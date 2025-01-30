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
    page_title="PDF Text Extractor",
    page_icon="📄",
    layout="centered"
)

# Title of the application
st.title("📄 PDF Text Extractor")

# Load environment variables
load_dotenv()

working_dir = os.path.dirname(os.path.abspath(__file__))
config_data = json.load(open(f"{working_dir}/config.json"))

# Save the API key to environment variable
os.environ["GROQ_API_KEY"] = config_data["GROQ_API_KEY"]

# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Add these new helper functions
def get_alternative_models():
    """Get available Groq models."""
    return {
        "primary": "mixtral-8x7b-32768",  # Mixtral model
        "fallback": "llama2-70b-4096"     # Llama2 model as fallback
    }

# Function to search for financial terms in the text
def search_financial_terms(text, terms, quarter):
    results = {}
    for term in terms:
        # Use regex to find the term and capture the value
        pattern = rf"{term}.*?(\d[\d,\.]*)"  # Adjust regex as needed
        matches = re.findall(pattern, text, re.IGNORECASE)
        results[term] = matches
    return results

def extract_text_from_pdf(file):
    """Extract text from PDF file with improved accuracy."""
    text = ""
    try:
        # First attempt with pdfplumber with enhanced settings
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                # Extract text with custom settings
                text += page.extract_text(
                    x_tolerance=3,  # Adjust character spacing tolerance
                    y_tolerance=3,  # Adjust line spacing tolerance
                    layout=True,    # Maintain layout
                    keep_blank_chars=False,  # Remove unnecessary spaces
                    use_text_flow=True,      # Better handle columns
                    horizontal_ltr=True      # Left to right text
                ) or ""
                text += "\n\n"  # Add spacing between pages
        
        # Clean up the extracted text
        text = clean_extracted_text(text)
        
        if not text.strip():  # If no text was extracted, try PyPDF2
            raise Exception("No text extracted with pdfplumber")
            
    except Exception as e:
        st.warning(f"Trying alternative PDF extraction method: {str(e)}")
        try:
            # Fallback to PyPDF2 with improved handling
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                # Apply the same cleaning to PyPDF2 output
                text += clean_extracted_text(page_text) + "\n\n"
        except Exception as e:
            st.error(f"Failed to extract text from PDF: {str(e)}")
            return ""
    
    return text

def clean_extracted_text(text):
    """Clean and normalize extracted text."""
    import re
    
    if not text:
        return ""
    
    # Series of cleaning operations
    cleaned = text
    
    # Remove excessive whitespace while preserving newlines
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Fix common OCR issues
    cleaned = cleaned.replace('|', 'I')  # Common OCR mistake
    cleaned = cleaned.replace('Rs,', 'Rs.')  # Fix common currency format issues
    cleaned = cleaned.replace('Rs ', 'Rs. ')  # Standardize currency notation
    
    # Fix number formatting
    cleaned = re.sub(r'(?<=\d),(?=\d{3})', '', cleaned)  # Fix thousand separators
    cleaned = re.sub(r'(?<=\d) (?=\d{3})', ',', cleaned)  # Add proper thousand separators
    
    # Fix common unit formatting
    cleaned = re.sub(r'(?i)cr\.?$', 'cr', cleaned)  # Standardize 'cr' notation
    cleaned = re.sub(r'(?i)crores?', 'cr', cleaned)  # Standardize 'crores' to 'cr'
    cleaned = re.sub(r'(?i)lakhs?', 'lakh', cleaned)  # Standardize 'lakhs'
    
    # Fix quarter notation
    cleaned = re.sub(r'Q(\d)\s+FY', r'Q\1FY', cleaned)  # Remove space between Q and FY
    cleaned = re.sub(r'(?i)quarter\s+(\d)', r'Q\1', cleaned)  # Standardize quarter notation
    
    # Remove unnecessary characters
    cleaned = re.sub(r'[^\S\n]+', ' ', cleaned)  # Remove multiple spaces but keep newlines
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # Normalize multiple newlines
    
    return cleaned.strip()

def extract_text_from_docx(file):
    """Extract text from DOCX file with improved accuracy."""
    try:
        doc = docx.Document(file)
        
        # Extract text with paragraph formatting
        paragraphs = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # Skip empty paragraphs
                # Preserve formatting and structure
                text = paragraph.text.strip()
                # Clean the extracted text
                text = clean_extracted_text(text)
                paragraphs.append(text)
        
        # Join paragraphs with double newlines for better structure
        text = '\n\n'.join(paragraphs)
        return text
    except Exception as e:
        st.error(f"Failed to extract text from DOCX: {str(e)}")
        return ""

def display_extracted_text(text):
    """Display extracted text with debugging information."""
    st.subheader("Extracted Text Analysis")
    
    # Show text statistics
    st.write("Text Statistics:")
    stats = {
        "Total Characters": len(text),
        "Total Words": len(text.split()),
        "Total Lines": len(text.splitlines()),
        "Contains Numbers": bool(re.search(r'\d', text)),
        "Contains Currency Symbols": bool(re.search(r'Rs\.?|₹', text)),
        "Contains Quarter References": bool(re.search(r'Q[1-4]|quarter', text, re.IGNORECASE))
    }
    st.write(stats)
    
    # Display the actual text in an expandable section
    with st.expander("View Extracted Text"):
        st.text(text)
        
        # Add download button for the extracted text
        st.download_button(
            label="Download Extracted Text",
            data=text,
            file_name="extracted_text.txt",
            mime="text/plain"
        )

def standardize_financial_terms(terms):
    """Standardize financial terms to common formats."""
    term_mapping = {
    "revenue": ["revenue", "operating revenue", "total revenue", "income", "net revenue", "gross revenue", "sales revenue", "turnover"],
    "pat": ["pat", "profit after tax", "net profit", "profit", "net earnings", "earnings after tax", "net income", "bottom line"],
    "ebitda": ["ebitda", "operating profit", "earnings before interest, tax, depreciation and amortization", "core earnings", "operating income"],
    "net worth": ["net worth", "networth", "total net worth", "shareholder equity", "equity", "book value"],
    "eps": ["eps", "earnings per share", "basic eps", "diluted eps"],
    "total assets": ["total assets", "assets", "gross assets", "net assets", "asset base"],
    "total liabilities": ["total liabilities", "liabilities", "debt", "borrowings", "obligations"],
    "equity": ["equity", "shareholder equity", "total equity", "owner's equity"],
    "operating expenses": ["operating expenses", "opex", "total expenses", "operating costs"],
    "finance cost": ["finance cost", "interest expense", "borrowing cost", "debt servicing cost"],
    "dividend": ["dividend", "dividends declared", "interim dividend", "final dividend", "dividend payout"],
    "cash flow": ["cash flow", "net cash flow", "operating cash flow", "free cash flow", "fcf"],
    "market capitalization": ["market capitalization", "market cap", "valuation"],
    "gross profit": ["gross profit", "gross earnings", "gross margin"],
    "operating margin": ["operating margin", "ebitda margin", "operating profit margin"],
    "net margin": ["net margin", "net profit margin", "profit margin"],
    "return on equity": ["return on equity", "roe"],
    "return on assets": ["return on assets", "roa"],
    "return on investment": ["return on investment", "roi"],
    "debt to equity ratio": ["debt to equity ratio", "d/e ratio"],
    "interest coverage ratio": ["interest coverage ratio", "debt service coverage ratio", "icr"],
    "current ratio": ["current ratio", "liquidity ratio"],
    "quick ratio": ["quick ratio", "acid-test ratio"],
    "aum": ["aum", "assets under management", "total aum", "funds under management"],
    "loan book": ["loan book", "loan portfolio", "total loans", "loan outstanding"],
    "npa": ["npa", "non-performing assets", "bad loans"],
    "provisions": ["provisions", "loan loss provisions", "bad debt reserves"],
    "interest income": ["interest income", "net interest income", "interest earnings"],
    "fee and commission income": ["fee income", "commission income", "brokerage income"],
    "other income": ["other income", "miscellaneous income", "non-operating income"],
    "capital adequacy ratio": ["capital adequacy ratio", "car", "crar"],
    "tier 1 capital": ["tier 1 capital", "core capital"],
    "tier 2 capital": ["tier 2 capital", "supplementary capital"],
    "risk-weighted assets": ["risk-weighted assets", "rwa"],
    "investment book": ["investment book", "investment portfolio"],
}

    
    standardized_terms = []
    for term in terms:
        term = term.lower().strip()
        for standard_term, variations in term_mapping.items():
            if term in variations:
                standardized_terms.append(standard_term.upper())
                break
        else:
            standardized_terms.append(term.upper())
    
    return standardized_terms

def get_llm_response(text, terms, quarter, year):
    """Get financial values using Groq for specific terms, quarter and year."""
    # Create variations of quarter format
    quarter_num = quarter[1]  # Get the quarter number (e.g., '3' from 'Q3')
    fiscal_year = str(year)[2:] # Get last 2 digits of year (e.g., '25' from '2025')
    
    quarter_variations = [
        quarter,                    # "Q3"
        quarter.lower(),           # "q3"
        f"quarter ended December",  # "quarter ended December" (for Q3)
        f"quarter ended September", # "quarter ended September" (for Q2)
        f"quarter ended June",      # "quarter ended June" (for Q1)
        f"quarter ended March",     # "quarter ended March" (for Q4)
        f"quarter {quarter[1]}",   # "quarter 3"
        f"Quarter {quarter[1]}",   # "Quarter 3"
        f"{quarter[1]}rd quarter" if quarter[1] == '3' else   # "3rd quarter"
        f"{quarter[1]}th quarter" if quarter[1] in ['1','2','4'] else "",  # "1st/2nd/4th quarter"
        f"{quarter[1]}Q",          # "3Q"
        f"{quarter}FY{fiscal_year}",  # "Q3FY25"
        f"{quarter} FY{fiscal_year}",  # "Q3 FY25"
        f"{quarter.lower()}fy{fiscal_year}",  # "q3fy25"
        f"{quarter.lower()}fy{fiscal_year}",  # "q3 fy25"
        f"{quarter[1]}QFY{fiscal_year}",  # "3QFY25"
        f"Q{quarter[1]} FY{fiscal_year}"  # "Q3 FY25"
    ]
    
    # Search for any variation of the quarter
    search_positions = []
    text_lower = text.lower()
    
    for q_variant in quarter_variations:
        if not q_variant:  # Skip empty variations
            continue
        # Look for quarter variant near the year
        for i in range(len(text_lower)):
            if text_lower[i:].startswith(q_variant.lower()) or \
               (quarter == "Q3" and "quarter ended december" in text_lower[i:i+25]):
                search_positions.append(i)
    
    if not search_positions:
        st.warning(f"Could not find mentions of {quarter} {year} in the text")
        return {}
    
    # Use the first found position
    pos = search_positions[0]
    
    # Extract a window of text around the mention (4000 chars before and after)
    start = max(0, pos - 4000)
    end = min(len(text), pos + 4000)
    truncated_text = text[start:end]
    
    prompt = f"""
    Task: You are a financial data extraction expert. Extract the EXACT financial values from the given text.

    Search for these specific terms: {', '.join(terms)}
    Time period: {quarter}FY{str(year)[2:]} or {quarter} {year} or quarter ended December 31, {year}

    Rules:
    1. Look for statements like:
       - "Operating PAT for Q3FY25 at Rs. 525 cr"
       - "Consolidated operating PAT for Q3FY25 at Rs. 525 cr"
       - "PAT for Q3FY25 at Rs. 525 cr"
       - "YoY growth in Q3FY25 PAT to Rs. 234 cr"
    2. Extract the EXACT numerical values as they appear, do not modify or calculate
    3. Double check the time period matches exactly
    4. Verify the value corresponds to the correct term (don't mix up different metrics)
    5. If multiple values exist, use the most recent or consolidated figure
    6. Include the units exactly as shown (cr, crores, lakhs)

    Required format:
    {{
        "<term>": "Rs. X cr",
        ...
    }}

    Example of correct extraction:
    If text contains "Operating PAT for Q3FY25 at Rs. 525 cr", return:
    {{
        "Operating PAT": "Rs. 525 cr"
    }}

    Important: Return ONLY the JSON object, no explanations.

    Context:
    {truncated_text}
    """
    
    models = get_alternative_models()
    try:
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise financial data extraction tool. Extract EXACT numbers as they appear in the text, without any modifications. Focus on finding the exact matches for the specified time period."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=models["primary"],
            temperature=0,
            max_tokens=1000
        )
        
        # Get the response content
        response_text = completion.choices[0].message.content.strip()
        
        # Try to parse the JSON, if it fails, attempt to clean it
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON if there's additional text
            try:
                # Look for JSON-like structure
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    cleaned_json = response_text[json_start:json_end]
                    return json.loads(cleaned_json)
            except:
                st.error(f"Could not parse LLM response as JSON: {response_text}")
                return {}
            
    except Exception as e:
        st.error(f"Error getting LLM response: {str(e)}")
        return {}

def main():
    st.title("Financial Document Analysis")
    
    uploaded_file = st.file_uploader("Upload a PDF or DOCX file", type=['pdf', 'docx'])
    
    if uploaded_file:
        # Extract text based on file type
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
        else:
            text = extract_text_from_docx(uploaded_file)
        
        # Display extracted text with analysis
        display_extracted_text(text)
        
        # Input fields for terms, quarter, and year
        terms = st.text_input("Enter terms to search (comma-separated)", 
                            "Revenue, PAT, EBITDA").split(',')
        terms = [term.strip() for term in terms]
        
        quarter = st.selectbox("Select Quarter", ["Q1", "Q2", "Q3", "Q4"])
        year = st.number_input("Enter Year", min_value=2000, max_value=2100, value=2024)
        
        if st.button("Analyze"):
            if text:
                with st.spinner("Analyzing document..."):
                    terms = standardize_financial_terms(terms)
                    results = get_llm_response(text, terms, quarter, year)
                    
                    if results:
                        # Display results in a table
                        df = pd.DataFrame(list(results.items()), columns=['Term', 'Value'])
                        st.table(df)
                    else:
                        st.warning("No results found.")
            else:
                st.error("No text could be extracted from the document.")

if __name__ == "__main__":
    main()