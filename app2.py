import os
import json
import re
import datetime
import pandas as pd
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
from unstract.llmwhisperer import LLMWhispererClientV2

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
os.environ["LLMWHISPERER_API_KEY"] = config_data["LLMWHISPERER_API_KEY"]
# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Initialize LLMWhisperer client
whisper_client = LLMWhispererClientV2(base_url="https://llmwhisperer-api.unstract.com/v1", api_key=os.getenv('LLMWHISPERER_API_KEY'))

def extract_text_from_pdf(file):
    """Extracts text from PDF using LLMWhisperer."""
    try:

        with open("temp.pdf", 'wb') as f:
            f.write(file.read())
        st.success(f"PDF saved locally as temp.pdf")
        
        client = LLMWhispererClientV2()
        try:
            result = client.whisper(
                        file_path="temp.pdf",
                        wait_for_completion=True,
                        wait_timeout=200,
                    )
            print(result)
        except Exception as e:
            print(e)
        
        # Debug: Print raw response
        st.write("Raw API Response:", response)
        
        # Handle response based on type
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                # If it's a plain text response, wrap it
                response = {'text': response}
        
        # Check if the response contains text
        if response and 'text' in response:
            text = response['text']
            if not text.strip():
                st.warning("No text extracted from the PDF.")
                return ""
            return clean_extracted_text(text)
        else:
            st.warning("No text found in the response.")
            return ""
    except Exception as e:
        st.error(f"Error during text extraction: {str(e)}")
        # Debug: Print the full error traceback
        import traceback
        st.error(f"Full error: {traceback.format_exc()}")
        return ""

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
        "ebitda": ["ebitda", "earnings before interest, tax, depreciation"],
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

def map_quarter_to_date(quarter, year):
    """Maps quarter to specific date ranges and end dates."""
    quarter_date_mapping = {
        "Q1": {
            "start_date": f"April 1, {year-1}",
            "end_date": f"June 30, {year-1}",
            "calendar_end_date": f"June 30, {year-1}"
        },
        "Q2": {
            "start_date": f"July 1, {year-1}",
            "end_date": f"September 30, {year-1}",
            "calendar_end_date": f"September 30, {year-1}"
        },
        "Q3": {
            "start_date": f"October 1, {year-1}",
            "end_date": f"December 31, {year-1}",
            "calendar_end_date": f"December 31, {year-1}"
        },
        "Q4": {
            "start_date": f"January 1, {year}",
            "end_date": f"March 31, {year}",
            "calendar_end_date": f"March 31, {year}"
        }
    }
    return quarter_date_mapping.get(quarter, {})

def correlate_quarter_data(text, quarter, year):
    """Correlates quarter-based financial data with specific dates."""
    quarter_dates = map_quarter_to_date(quarter, year)
    
    financial_data = extract_llm_response(text, 
                                          ["Revenue", "PAT", "EBITDA"], 
                                          quarter, 
                                          year)
    
    correlated_data = {
        "Quarter": quarter,
        "Fiscal Year": f"FY{str(year)[2:]}",
        "Start Date": quarter_dates.get("start_date", "N/A"),
        "End Date": quarter_dates.get("end_date", "N/A"),
        "Calendar End Date": quarter_dates.get("calendar_end_date", "N/A"),
        **financial_data
    }
    
    return correlated_data

def validate_date_correlation(correlated_data):
    """Validates the correlation between quarter and dates."""
    required_keys = ["Quarter", "Fiscal Year", "Start Date", "End Date", "Calendar End Date"]
    return all(key in correlated_data for key in required_keys)

def validate_quarter(quarter):
    """Validate and standardize quarter input."""
    quarter = quarter.upper().strip()
    valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    
    if quarter in valid_quarters:
        return quarter
    
    # Try to match variations
    quarter_mapping = {
        '1ST': 'Q1',
        'FIRST': 'Q1',
        '2ND': 'Q2',
        'SECOND': 'Q2',
        '3RD': 'Q3',
        'THIRD': 'Q3',
        '4TH': 'Q4',
        'FOURTH': 'Q4'
    }
    
    if quarter in quarter_mapping:
        return quarter_mapping[quarter]
    
    # Attempt to parse numeric inputs
    try:
        num = int(quarter)
        if 1 <= num <= 4:
            return f'Q{num}'
    except ValueError:
        pass
    
    return None

def intelligent_year_parsing(year_input):
    """Intelligently parse year input with various formats."""
    try:
        # Direct integer input
        year = int(year_input)
        if 2000 <= year <= 2100:
            return year
        
        # Handle short year formats
        if len(str(year_input)) == 2:
            current_century = datetime.datetime.now().year // 100
            year = int(f"{current_century}{year_input}")
            return year
        
        # Handle fiscal year notation
        if str(year_input).startswith('FY'):
            try:
                return int(year_input[2:]) + 2000
            except ValueError:
                return None
    
    except (ValueError, TypeError):
        # Handle text-based inputs
        year_mapping = {
            'CURRENT': datetime.datetime.now().year,
            'PREVIOUS': datetime.datetime.now().year - 1,
            'LAST': datetime.datetime.now().year - 1
        }
        
        year_input = str(year_input).upper()
        return year_mapping.get(year_input)
    
    return None

def main():
    st.title("🔍 Intelligent Financial Data Extractor")

    # File Upload
    uploaded_file = st.file_uploader("Upload Financial Report (PDF)", type=['pdf'])
    
    # Free-form Input Sections
    st.subheader("Financial Analysis Parameters")
    
    # Quarter Input with Intelligence
    quarter_input = st.text_input(
        "Enter Quarter (Q1/Q2/Q3/Q4)", 
        placeholder="E.g., Q3, 3rd, First Quarter"
    )
    
    # Year Input with Intelligence
    year_input = st.text_input(
        "Enter Fiscal Year", 
        placeholder="E.g., 2024, FY24, Current"
    )
    
    # Financial Terms with Free-form Input
    terms_input = st.text_input(
        "Enter Financial Terms (Comma Separated)", 
        placeholder="E.g., Revenue, Profit, EBITDA, EPS"
    )

    # Analysis Mode Selection
    analysis_mode = st.radio(
        "Select Analysis Mode",
        ["Basic Extraction", "Detailed Correlation", "Comprehensive Analysis"]
    )

    # Validation and Processing
    if uploaded_file:
        # Validate Inputs
        validated_quarter = validate_quarter(quarter_input)
        validated_year = intelligent_year_parsing(year_input)
        
        # Split and clean terms
        terms = [term.strip() for term in terms_input.split(',') if term.strip()]
        
        # Input Validation Checks
        input_valid = True
        
        if not validated_quarter:
            st.error("Invalid Quarter Input. Please use Q1-Q4 or similar formats.")
            input_valid = False
        
        if not validated_year:
            st.error("Invalid Year Input. Use numeric year or descriptive terms.")
            input_valid = False
        
        if not terms:
            st.warning("No financial terms specified. Using default terms.")
            terms = ["Revenue", "PAT", "EBITDA"]

        # Proceed with Analysis
        if input_valid and st.button("🚀 Analyze Financial Data"):
            with st.spinner("Processing Document..."):
                # Text Extraction
                text = extract_text_from_pdf(uploaded_file)
                
                # Standardize Terms
                standardized_terms = standardize_financial_terms(terms)

                # Conditional Analysis
                if analysis_mode == "Basic Extraction":
                    results = extract_llm_response(
                        text, 
                        standardized_terms, 
                        validated_quarter, 
                        validated_year
                    )
                    
                    if results:
                        df = pd.DataFrame(list(results.items()), columns=['Term', 'Value'])
                        st.table(df)
                    else:
                        st.warning("No relevant data found.")

                elif analysis_mode == "Detailed Correlation":
                    correlated_data = correlate_quarter_data(
                        text, 
                        validated_quarter, 
                        validated_year
                    )
                    
                    if validate_date_correlation(correlated_data):
                        correlation_df = pd.DataFrame.from_dict(
                            correlated_data, 
                            orient='index', 
                            columns=['Value']
                        )
                        st.table(correlation_df)
                    else:
                        st.warning("Correlation incomplete.")

                elif analysis_mode == "Comprehensive Analysis":
                    # Combine extraction methods
                    results = extract_llm_response(
                        text, 
                        standardized_terms, 
                        validated_quarter, 
                        validated_year
                    )
                    
                    correlated_data = correlate_quarter_data(
                        text, 
                        validated_quarter, 
                        validated_year
                    )
                    
                    # Display comprehensive results
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Financial Metrics")
                        results_df = pd.DataFrame(list(results.items()), columns=['Term', 'Value'])
                        st.table(results_df)
                    
                    with col2:
                        st.subheader("Date Correlation")
                        correlation_df = pd.DataFrame.from_dict(
                            correlated_data, 
                            orient='index', 
                            columns=['Value']
                        )
                        st.table(correlation_df)

    # Helper Information
    st.sidebar.info("""
    💡 Intelligent Input Tips:
    - Quarter: Q1, 1st, First Quarter
    - Year: 2024, FY24, Current
    - Terms: Revenue, Profit, Multiple terms supported
    """)

if __name__ == "__main__":
    main()