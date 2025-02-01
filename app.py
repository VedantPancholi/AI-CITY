import streamlit as st
import PyPDF2
import json
import os
import tempfile
import google.generativeai as genai
import re
from datetime import datetime

class FinancialDataExtractor:
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as config_file:
            config_data = json.load(config_file)
        
        gemini_api_key = config_data.get('GEMINI_API_KEY')
        if not gemini_api_key:
            raise ValueError("Gemini API key not found in config file")
        
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Initialize cache in session state
        st.session_state.setdefault("pdf_chunks", {})
        st.session_state.setdefault("chunk_extractions", {})
        st.session_state.setdefault("raw_extractions", [])
        st.session_state.setdefault("consolidated_data", None)

    def convert_date_to_fiscal_quarter(self, date_str):
        try:
            date_obj = datetime.strptime(date_str, '%d %b %Y')
            month = date_obj.month
            year = date_obj.year
            
            if month in [1, 2, 3]:
                quarter = 'Q4'
                fiscal_year = f'FY{str(year)[-2:]}'
            elif month in [4, 5, 6]:
                quarter = 'Q1'
                fiscal_year = f'FY{str(year + 1)[-2:]}'
            elif month in [7, 8, 9]:
                quarter = 'Q2'
                fiscal_year = f'FY{str(year + 1)[-2:]}'
            else:
                quarter = 'Q3'
                fiscal_year = f'FY{str(year + 1)[-2:]}'
            
            return f'{quarter}{fiscal_year}'
        except:
            return "Unknown"

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF and divide into chunks of 5 pages."""
        try:
            chunks = {}
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                # Create chunks of 5 pages
                for i in range(0, total_pages, 5):
                    chunk_text = []
                    for j in range(i, min(i + 5, total_pages)):
                        text = pdf_reader.pages[j].extract_text()
                        if text:
                            chunk_text.append(text)
                    
                    if chunk_text:
                        chunks[f"chunk_{i//5}"] = '\n\n'.join(chunk_text)
            
            return chunks
        except Exception as e:
            st.error(f"Error extracting text: {str(e)}")
            return {}

    def query_financial_data(self, user_query):
        """Search for financial details in the cached consolidated data."""
        if not st.session_state.consolidated_data:
            return "No financial data available. Please extract data first."

        try:
            search_prompt = """
            Given the following financial data and user query, please provide a specific and concise answer.
            Only return information that is directly relevant to the query.
            
            Financial Data:
            {data}
            
            User Query: {query}
            """
            
            response = self.model.generate_content(
                search_prompt.format(
                    data=st.session_state.consolidated_data,
                    query=user_query
                )
            )
            
            if not response or not response.text:
                return "No relevant information found"
                
            return response.text
            
        except Exception as e:
            st.error(f"Error searching data: {str(e)}")
            return "Error processing query"

    def extract_financial_data(self, text):
        """Extract financial data from text using Gemini AI."""
        try:
            prompt = """
            You are a financial data extraction expert. Please analyze the following text and extract all financial information.
            
            Focus on extracting:
            1. All numerical figures with their context
            2. Financial metrics and KPIs
            3. Revenue, profit, and loss figures
            4. Growth percentages and trends
            5. Market-related figures
            6. Any other relevant financial data
            
            Format your response as a clear markdown list, grouping similar items together.
            Each data point should include its full context and any relevant time period or date.
            
            Text to analyze:
            {text}
            """
            
            response = self.model.generate_content(prompt.format(text=text))
            
            # Check if response is empty or error occurred
            if not response or not response.text:
                return "No financial data could be extracted"
                
            return response.text
            
        except Exception as e:
            st.error(f"Error extracting financial data: {str(e)}")
            return "Error processing financial data"

    def process_pdf(self, pdf_path):
        """Process PDF in chunks and cache the results."""
        try:
            # Extract text in chunks
            chunks = self.extract_text_from_pdf(pdf_path)
            if not chunks:
                return "No text could be extracted from the PDF"
            
            # Store chunks in session state
            st.session_state.pdf_chunks = chunks
            
            # Process each chunk and store results
            all_extractions = []
            for chunk_id, chunk_text in chunks.items():
                # Check if chunk has been processed before
                if chunk_id not in st.session_state.chunk_extractions:
                    extracted_data = self.extract_financial_data(chunk_text)
                    st.session_state.chunk_extractions[chunk_id] = extracted_data
                
                all_extractions.append(st.session_state.chunk_extractions[chunk_id])
            
            # Merge all extractions
            consolidated_data = self.merge_extractions(all_extractions)
            st.session_state.consolidated_data = consolidated_data
            
            return consolidated_data
            
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return "Error processing PDF"

    def merge_extractions(self, extractions):
        """Merge multiple extraction results into a single consolidated view."""
        try:
            merged_prompt = """
            You are a financial data consolidation expert. Below are multiple extractions from different parts of a document.
            Please merge this information into a single, coherent summary. Remove any duplicates and organize related information together.
            
            Previous extractions:
            {extractions}
            """
            
            # Join all extractions with clear separation
            all_extractions = "\n\n--- Next Section ---\n\n".join(extractions)
            
            response = self.model.generate_content(merged_prompt.format(extractions=all_extractions))
            
            if not response or not response.text:
                return "Could not consolidate the extracted data"
                
            return response.text
            
        except Exception as e:
            st.error(f"Error merging extractions: {str(e)}")
            return "Error consolidating data"

def main():
    st.set_page_config(page_title="Financial PDF Extractor", page_icon="📊", layout="wide")
    st.title("📊 Financial PDF Data Extractor")

    try:
        extractor = FinancialDataExtractor()
    except Exception as e:
        st.error(f"Initialization Error: {e}")
        st.stop()
    
    uploaded_file = st.file_uploader("Upload Financial PDF", type=['pdf'])

    if uploaded_file:
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf.write(uploaded_file.getvalue())
        temp_pdf.close()

        with st.spinner("Processing PDF..."):
            extracted_data = extractor.process_pdf(temp_pdf.name)
            st.session_state.consolidated_data = extracted_data
            st.subheader("Extracted Financial Information")
            st.markdown(extracted_data)

        os.unlink(temp_pdf.name)
    
    if st.session_state.consolidated_data:
        st.subheader("Financial Data Query")
        user_query = st.text_input("Enter your specific financial query", placeholder="e.g., Total Revenue, Net Profit Margin")

        if st.button("Extract Specific Information"):
            if user_query:
                with st.spinner("Searching locally..."):
                    query_response = extractor.query_financial_data(user_query)
                    st.text_area("Query Result", query_response, height=300)


if __name__ == "__main__":
    main()
