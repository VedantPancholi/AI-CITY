import streamlit as st
import json
import os
import tempfile
import google.generativeai as genai
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import re

class FinancialReportAnalyzer:
    def __init__(self, config_path='config.json'):
        """
        Initialize the financial report analyzer by reading API keys from config.
        """
        with open(config_path, 'r') as config_file:
            config_data = json.load(config_file)
        
        gemini_api_key = config_data.get('GEMINI_API_KEY')
        if not gemini_api_key:
            raise ValueError("API key not found in config file")
        
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.extracted_data = None
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text and tables from the provided PDF file using pdfplumber.
        """
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text.strip()

    def extract_text_with_ocr(self, pdf_path):
        """
        Extract text from a PDF using OCR if the document is an image-based PDF.
        """
        images = convert_from_path(pdf_path)
        text = ""
        for image in images:
            text += pytesseract.image_to_string(image) + "\n"
        return text.strip()

    def extract_numeric_data(self, text):
        """
        Extract structured financial data from text using Gemini LLM.
        """
        prompt = f"""
        Please analyze the following document text and extract any relevant financial data. The document might contain revenue, profit, EBITDA, and other financial metrics.
        Document Text:
        {text}
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()  # Ensure it's not empty

            if not response_text:
                raise ValueError("Gemini API returned an empty response.")

            # Try parsing JSON safely
            try:
                self.extracted_data = json.loads(response_text)
                return self.extracted_data
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON response from Gemini: {response_text}")

        except Exception as e:
            st.error(f"Error extracting data: {str(e)}")
            return None

    def parse_user_query(self, user_query):
        """
        Parse user query for financial data extraction.
        """
        patterns = {
            'metric_with_period': r'(.*?)\s*for\s*(Q\d\s*FY\d{2,4}|\bFY\d{2,4}\b|\b\d{4}\b)',
            'metric_only': r'^(.*?)$'
        }
        
        period_match = re.match(patterns['metric_with_period'], user_query, re.IGNORECASE)
        if period_match:
            return {'metric': period_match.group(1).strip(), 'period': period_match.group(2).strip()}
        
        metric_match = re.match(patterns['metric_only'], user_query, re.IGNORECASE)
        if metric_match:
            return {'metric': metric_match.group(1).strip(), 'period': None}
        
        return None
    
    def find_numeric_data(self, parsed_query):
        """
        Retrieve the requested financial metric from extracted data.
        """
        if not self.extracted_data:
            return "No extracted data available. Run extraction first."
        
        metric, period = parsed_query['metric'], parsed_query['period']
        
        result = ""
        if period:
            for category in ['Quarterly Data', 'Annual Data']:
                if period in self.extracted_data.get(category, {}):
                    value = self.extracted_data[category][period].get(metric)
                    if value:
                        result = f"{metric} for {period}: {value}"
                        break
        else:
            value = self.extracted_data['Financial Metrics'].get(metric)
            if value:
                result = f"{metric}: {value}"
        
        return result if result else "Metric not found in extracted data."

def main():
    st.set_page_config(page_title="Financial Report Analyzer", page_icon="📊", layout="wide")
    st.title("📊 Financial Report Analyzer")
    
    try:
        with open('config.json', 'r') as config_file:
            config_data = json.load(config_file)
        
        gemini_api_key = config_data.get("GEMINI_API_KEY")
        if not gemini_api_key:
            st.error("API key is missing in the config file.")
            return
        
        analyzer = FinancialReportAnalyzer()
    except Exception as e:
        st.error(f"Configuration Error: {str(e)}")
        return
    
    uploaded_file = st.file_uploader("Upload Financial PDF", type=['pdf'], help="Upload a PDF financial document")
    
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        with st.spinner("Extracting text from PDF..."):
            pdf_text = analyzer.extract_text_from_pdf(tmp_file_path)
            if not pdf_text:  # If no text is extracted, try OCR
                st.warning("No text extracted from the PDF. Trying OCR...")
                pdf_text = analyzer.extract_text_with_ocr(tmp_file_path)
        
        with st.spinner("Extracting numeric data..."):
            extracted_data = analyzer.extract_numeric_data(pdf_text)
        
        st.subheader("Query Financial Data")
        user_query = st.text_input("Enter your query", placeholder="e.g., Net Profit for Q3 FY25")
        
        if st.button("Get Data"):
            parsed_query = analyzer.parse_user_query(user_query)
            if not parsed_query:
                st.error("Invalid query format. Try again.")
            else:
                with st.spinner("Fetching data..."):
                    response = analyzer.find_numeric_data(parsed_query)
                st.success("Query Completed")
                st.code(response, language="markdown")
        
if __name__ == "__main__":
    main()
