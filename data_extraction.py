import streamlit as st
import pandas as pd
import re
import os
from io import StringIO
from dotenv import load_dotenv
from agentic_doc.parse import parse
import tempfile

# Set page configuration
st.set_page_config(
    page_title="Document Table Extractor",
    page_icon="📄",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

# App title
st.markdown('<div class="main-header">📄 Document Table Extractor</div>', unsafe_allow_html=True)

def setup_api_key():
    """Setup API key for both local and Streamlit Cloud environments"""
    try:
        # First try to get API key from Streamlit secrets (for Streamlit Cloud)
        if 'VISION_AGENT_API_KEY' in st.secrets:
            os.environ['VISION_AGENT_API_KEY'] = st.secrets['VISION_AGENT_API_KEY']
            st.sidebar.success("✅ API Key loaded from Streamlit Secrets")
            return True
        else:
            # Fallback to .env file (for local development)
            load_dotenv()
            api_key = os.getenv("LANDING_API_KEY")
            if api_key:
                os.environ['VISION_AGENT_API_KEY'] = api_key
                st.sidebar.info("ℹ️ API Key loaded from .env file")
                return True
            else:
                st.sidebar.error("❌ No API key found. Please check your configuration.")
                return False
    except Exception as e:
        st.sidebar.error(f"❌ Error setting up API key: {str(e)}")
        return False

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    st.info("Upload a PDF document to extract tables using AI-powered parsing.")
    
    # Setup API key
    api_key_verified = setup_api_key()

def validate_file(file):
    """Validate uploaded file"""
    if file is not None:
        if file.type != "application/pdf":
            return False, "Please upload a PDF file"
        if file.size > 50 * 1024 * 1024:  # 50MB limit
            return False, "File size must be less than 50MB"
        return True, "File is valid"
    return False, "No file uploaded"

def extract_tables_from_pdf(file_path):
    """Extract tables from PDF using your existing logic"""
    try:
        results = parse(file_path)
        all_dataframes = []
        
        for idx, result in enumerate(results):
            markdown_content = result.markdown
            tables = re.findall(r"<table.*?>.*?</table>", markdown_content, re.DOTALL)
            
            for table_html in tables:
                df_list = pd.read_html(StringIO(table_html))
                for df in df_list:
                    df['source_page'] = idx + 1
                    df['table_id'] = f"page_{idx+1}_table_{len(all_dataframes) + 1}"
                    all_dataframes.append(df)
        
        return all_dataframes, len(results)
    
    except Exception as e:
        st.error(f"Error extracting tables: {str(e)}")
        return [], 0

def main():
    # Check if API key is available
    if not api_key_verified:
        st.error("""
        ❌ API Key not configured properly. Please setup your API key:
        
        **For Streamlit Cloud:**
        1. Go to your app settings
        2. Click on 'Secrets'
        3. Add your API key:
        ```
        VISION_AGENT_API_KEY = "your_actual_api_key_here"
        ```
        
        **For Local Development:**
        - Make sure you have a `.env` file with:
        ```
        LANDING_API_KEY=your_actual_api_key_here
        ```
        """)
        return

    # File upload section
    uploaded_file = st.file_uploader(
        "Choose a PDF file", 
        type="pdf",
        help="Upload a PDF document to extract tables"
    )
    
    # Validate file
    is_valid, validation_msg = validate_file(uploaded_file)
    
    if not is_valid and uploaded_file is not None:
        st.error(validation_msg)
        return
    
    if uploaded_file is not None:
        # Display file info
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**File name:** {uploaded_file.name}")
        with col2:
            st.info(f"**File size:** {uploaded_file.size / 1024:.2f} KB")
        
        # Extract tables button
        if st.button("Extract Tables", type="primary", use_container_width=True):
            with st.spinner("Parsing document and extracting tables..."):
                # Save uploaded file to temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    # Extract tables
                    dataframes, total_pages = extract_tables_from_pdf(tmp_file_path)
                    
                    # Display results
                    if dataframes:
                        st.success(f"✅ Successfully extracted {len(dataframes)} tables from {total_pages} pages")
                        
                        # Results summary
                        with st.container():
                            st.markdown("### 📊 Extraction Results")
                            
                            # Summary metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Tables", len(dataframes))
                            with col2:
                                st.metric("Total Pages", total_pages)
                            with col3:
                                total_rows = sum(len(df) for df in dataframes)
                                st.metric("Total Rows", total_rows)
                        
                        # Display individual tables
                        st.markdown("### 📋 Extracted Tables")
                        
                        for i, df in enumerate(dataframes):
                            with st.expander(f"Table {i+1} - Page {df['source_page'].iloc[0]}", expanded=i==0):
                                # Display the dataframe without technical columns for cleaner view
                                display_columns = [col for col in df.columns if col not in ['source_page', 'table_id']]
                                display_df = df[display_columns] if display_columns else df
                                
                                st.dataframe(
                                    display_df,
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                # Download button for individual table
                                csv_data = df.to_csv(index=False)
                                st.download_button(
                                    label=f"Download Table {i+1} as CSV",
                                    data=csv_data,
                                    file_name=f"table_{i+1}_page_{df['source_page'].iloc[0]}.csv",
                                    mime="text/csv",
                                    key=f"download_{i}"
                                )
                        
                        # Combined download section
                        st.markdown("### 💾 Download All Data")
                        
                        if len(dataframes) > 1:
                            combined_df = pd.concat(dataframes, ignore_index=True)
                            combined_csv = combined_df.to_csv(index=False)
                            
                            st.download_button(
                                label="Download All Tables as CSV",
                                data=combined_csv,
                                file_name="all_extracted_tables.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                            
                            # Preview combined data
                            with st.expander("Preview Combined Data"):
                                st.dataframe(combined_df, use_container_width=True)
                    
                    else:
                        st.warning("⚠️ No tables found in the document. The document was processed successfully but no tabular data was detected.")
                
                except Exception as e:
                    st.error(f"❌ Error processing document: {str(e)}")
                
                finally:
                    # Clean up temporary file
                    if os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)
    
    else:
        # Instructions when no file is uploaded
        st.markdown("""
        ### 📖 How to Use This App
        
        1. **Upload a PDF file** using the file uploader above
        2. **Click the 'Extract Tables' button** to process the document
        3. **View extracted tables** in interactive dataframes
        4. **Download individual tables** or all data as CSV files
        
        ### 🔧 Features
        
        - AI-powered table extraction from PDF documents
        - Multi-page document support
        - Interactive table preview with sorting and filtering
        - CSV export for individual tables and combined data
        - Real-time processing status
        
        ### ⚠️ Requirements
        
        - PDF documents with tabular data
        - Valid API key configured in Streamlit Secrets or .env file
        - File size under 50MB
        """)

if __name__ == "__main__":
    main()
