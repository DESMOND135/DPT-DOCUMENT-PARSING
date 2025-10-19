import streamlit as st
import pandas as pd
import re
import os
from io import StringIO
import tempfile

# Set page configuration - this should be the first Streamlit command
st.set_page_config(
    page_title="Document Table Extractor",
    page_icon="📄",
    layout="wide"
)

# Try to import dependencies with error handling
try:
    from dotenv import load_dotenv
    from agentic_doc.parse import parse
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    st.error(f"❌ Missing dependencies: {e}")
    DEPENDENCIES_AVAILABLE = False

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
    """Setup API key safely for both local and Streamlit Cloud environments"""
    try:
        # First try to get API key from Streamlit secrets (for Streamlit Cloud)
        if 'VISION_AGENT_API_KEY' in st.secrets:
            api_key = st.secrets['VISION_AGENT_API_KEY']
            os.environ['VISION_AGENT_API_KEY'] = str(api_key)
            return True, "✅ API Key loaded from Streamlit Secrets"
        
        # Fallback to .env file (for local development)
        if DEPENDENCIES_AVAILABLE:
            load_dotenv()
            api_key = os.getenv("LANDING_API_KEY")
            if api_key:
                os.environ['VISION_AGENT_API_KEY'] = str(api_key)
                return True, "✅ API Key loaded from .env file"
        
        return False, "❌ No API key found in secrets or .env file"
        
    except Exception as e:
        return False, f"❌ Error setting up API key: {str(e)}"

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
    """Extract tables from PDF using agentic_doc"""
    try:
        # Check if API key is set
        if 'VISION_AGENT_API_KEY' not in os.environ:
            st.error("API key not configured")
            return [], 0
            
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
    # Check dependencies first
    if not DEPENDENCIES_AVAILABLE:
        st.error("""
        ## 📦 Required Dependencies Missing
        
        Please make sure you have installed all required packages:
        ```bash
        pip install streamlit pandas python-dotenv agentic-doc
        ```
        """)
        return
    
    # Setup API key
    api_key_success, api_key_message = setup_api_key()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info("Upload a PDF document to extract tables using AI-powered parsing.")
        
        # Display API key status
        if api_key_success:
            st.success(api_key_message)
        else:
            st.error(api_key_message)
            
        st.markdown("---")
        st.markdown("### 🔑 API Key Setup")
        st.markdown("""
        **Streamlit Cloud:**
        - Go to Settings → Secrets
        - Add: `VISION_AGENT_API_KEY = "your_key"`
        
        **Local Development:**
        - Create `.env` file
        - Add: `LANDING_API_KEY=your_key`
        """)

    # Check if API key is available before proceeding
    if not api_key_success:
        st.error("""
        ## 🔑 API Key Configuration Required
        
        Please setup your API key to use this application:
        
        **For Streamlit Cloud Deployment:**
        1. Go to your app dashboard at [share.streamlit.io](https://share.streamlit.io)
        2. Click on your app
        3. Click the **'⋮'** (three dots) → **'Settings'** → **'Secrets'**
        4. Add your API key in this exact format:
        ```toml
        VISION_AGENT_API_KEY = "your_actual_api_key_here"
        ```
        
        **For Local Development:**
        1. Create a file called `.env` in your project root folder
        2. Add this line to the file:
        ```env
        LANDING_API_KEY=your_actual_api_key_here
        ```
        3. Make sure `.env` is in your `.gitignore` to keep it secret
        
        **Note:** Replace `"your_actual_api_key_here"` with your real API key from Landing AI.
        """)
        return

    # File upload section
    uploaded_file = st.file_uploader(
        "📤 Choose a PDF file", 
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
            st.info(f"**📄 File name:** {uploaded_file.name}")
        with col2:
            st.info(f"**📏 File size:** {uploaded_file.size / 1024:.2f} KB")
        
        # Extract tables button
        if st.button("🚀 Extract Tables", type="primary", use_container_width=True):
            with st.spinner("🔍 Parsing document and extracting tables..."):
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
                                    label=f"📥 Download Table {i+1} as CSV",
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
                                label="📥 Download All Tables as CSV",
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
                    st.info("This might be due to API key issues, network connectivity, or document format. Please check your configuration and try again.")
                
                finally:
                    # Clean up temporary file
                    try:
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
                    except:
                        pass  # Ignore cleanup errors
    
    else:
        # Instructions when no file is uploaded
        st.markdown("""
        ### 📖 How to Use This App
        
        1. **📤 Upload a PDF file** using the file uploader above
        2. **🚀 Click the 'Extract Tables' button** to process the document
        3. **📊 View extracted tables** in interactive dataframes
        4. **💾 Download individual tables** or all data as CSV files
        
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
        - Active internet connection for API calls
        """)

if __name__ == "__main__":
    main()
