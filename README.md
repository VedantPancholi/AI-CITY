
# **AI-Powered Financial Report Analyzer**  

### **Team: BYTEWISE**  
**Team Leader:** Vedant Pancholi

**Members:** Dhyey Thakkar | Vatsal Gajjar | Priyal Bhinde | Sachin Parmar  

## **Project Overview**  
Publicly listed companies release financial reports in PDF format, which contain unstructured financial data across multiple pages. Manually extracting key financial metrics is inefficient and error-prone. Our AI-powered financial report analyzer automates the extraction process for fast and accurate data retrieval.  

## **Problem Statement**  
- Manual data extraction is time-consuming and prone to errors.  
- Financial reports contain **text and tabular data**, making structured extraction challenging.  
- Extracting financial metrics like **Revenue, Net Profit, EBITDA, and Cash Flow** from PDFs is essential for investors and analysts.  

## **Solution Approach**  
1. **PDF Processing**  
   - Users upload a financial report (PDF).  
   - The document is **divided into chunks** of **5 pages** for efficient processing.  

2. **Data Extraction using AI/LLM**  
   - Each chunk is processed using **Gemini API or open-source LLMs**.  
   - Extracted financial metrics include:  
     ✅ Revenue/Sales  
     ✅ Net Profit  
     ✅ Operating Profit  
     ✅ EBITDA, EPS, Liabilities, Cash Flow, Total Assets, ROE  

3. **Data Consolidation & Preprocessing**  
   - Extracted data is **merged into a structured dataset**.  
   - **Error handling** ensures accuracy.  

4. **Cache-Based Querying**  
   - Extracted data is **cached** to prevent redundant computations.  
   - User queries are matched with cached data for **instant responses**.  

## **Features**  
✅ **Automated Extraction** – Eliminates manual work.  
✅ **High Accuracy** – AI-driven structured data extraction.  
✅ **Fast Processing** – Chunking speeds up analysis.  
✅ **Efficient Querying** – Cached data for quick lookups.  
✅ **Cost-Effective** – Reduces API calls & computational load.  

## **Challenges & Limitations**  
⚠ **Complex Report Formats** – Extracting data from scanned PDFs is difficult.  
⚠ **LLM Accuracy** – Fine-tuning required for financial terms.  
⚠ **Multi-language Support** – Currently optimized for **English** reports.  

## **Technologies Used**  
- **Python**  
- **PDF Processing** (pdfplumber, pdf2image)  
- **Gemini API**  
- **Pandas for Data Processing**  
- **Regex & JSON Caching**

## **Work Flow** 

![image](https://github.com/user-attachments/assets/80e6c747-9cb0-4366-b7d7-88d8732a3e97)


## **Installation & Setup**  

### **1. Clone the Repository**  
```bash
git clone https://github.com/VedantPancholi/AI-CITY.git
cd AI-CITY
```

### **2. Create a Virtual Environment**  
```bash
python -m venv venv
```

### **3. Activate the Virtual Environment**  
- **Windows**:  
  ```bash
  venv\Scripts\activate
  ```
- **Mac/Linux**:  
  ```bash
  source venv/bin/activate
  ```

### **4. Install Dependencies**  
```bash
pip install -r requirements.txt
```

### **5. Set Up API Key**  
Create a `config.json` file in the project root:  
```json
{
  "GEMINI_API_KEY": "your-api-key-here"
}
```

### **6. Run the Application**  
```bash
streamlit run app.py
```
