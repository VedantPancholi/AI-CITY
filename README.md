# AI-CITY
# Financial PDF Data Extractor

## Overview
The **Financial PDF Data Extractor** is a Streamlit-based web application that extracts, processes, and analyzes financial data from PDF documents. It leverages **Google Gemini AI** for intelligent data extraction and processing.

## Features
- Extracts financial data from PDFs
- Converts date formats into fiscal quarters
- Segments PDFs into chunks for efficient processing
- Uses AI to extract financial figures and metrics
- Allows users to query extracted financial data

## Technologies Used
- **Python**
- **Streamlit** (for the web interface)
- **PyPDF2** (for PDF text extraction)
- **Google Gemini AI** (for financial data analysis)
- **JSON** (for configuration management)
- **Tempfile & OS** (for handling temporary file storage)

## Installation
### Prerequisites
Ensure you have Python 3.7+ installed along with the following dependencies:
```bash
pip install streamlit PyPDF2 google-generativeai
```

### Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/your-repo/financial-pdf-extractor.git
   cd financial-pdf-extractor
   ```
2. Create a `config.json` file with your **Google Gemini AI API Key**:
   ```json
   {
       "GEMINI_API_KEY": "your_api_key_here"
   }
   ```
3. Run the application:
   ```bash
   streamlit run app.py
   ```

## Usage
1. Upload a financial PDF document.
2. The application will process the PDF and extract relevant financial information.
3. View extracted financial data in the interface.
4. Use the query feature to search for specific financial metrics.

## Functionality Breakdown
### `FinancialDataExtractor`
- **`convert_date_to_fiscal_quarter(date_str)`** - Converts a given date into fiscal quarters.
- **`extract_text_from_pdf(pdf_path)`** - Extracts and chunks text from PDFs.
- **`extract_financial_data(text)`** - Uses AI to extract financial figures and trends.
- **`query_financial_data(user_query)`** - Searches for specific financial details.
- **`process_pdf(pdf_path)`** - Processes PDFs and caches extracted data.
- **`merge_extractions(extractions)`** - Merges extracted financial data.

## Future Enhancements
- Support for additional file formats (CSV, Excel)
- Improved query accuracy using NLP
- Dashboard for financial data visualization


