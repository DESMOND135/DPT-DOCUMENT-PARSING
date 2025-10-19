import streamlit as st
import pandas as pd
import re
import os
from dotenv import load_dotenv
from agentic_doc.parse import parse
import tempfile
import base64

# Load environment variables
load_dotenv()

# Set API key
os.environ['VISION_AGENT_API_KEY'] = os.getenv("LANDING_API_KEY")

def parse_document(file_path):
    """Parse document and extract tables from ALL pages"""
    try:
        results = parse(file_path)
        
        all_dataframes = []
        markdown_contents = []
        
        # Check if we have multiple pages
        st.info(f"📄 Document contains {len(results)} pages")
        
        for idx, result in enumerate(results):
            markdown_content = result.markdown
            markdown_contents.append(markdown_content)
            
            # Debug information
            st.write(f"📖 Processing page {idx + 1}...")
            
            # Find all <table>...</table> blocks
            tables = re.findall(r"<table.*?>.*?</table>", markdown_content, re.DOTALL)
            
            # Debug table count
            if tables:
                st.write(f"✅ Found {len(tables)} tables on page {idx + 1}")
            else:
                st.write(f"ℹ️ No tables found on page {idx + 1}")
            
            # Convert each table to a pandas DataFrame
            for table_idx, table_html in enumerate(tables):
                try:
                    dfs = pd.read_html(table_html)
                    for df in dfs:
                        df['source_page'] = idx + 1
                        df['table_number'] = table_idx + 1
                        df['table_id'] = f"page_{idx+1}_table_{table_idx+1}"
                        all_dataframes.append(df)
                    st.success(f"📊 Successfully extracted table {table_idx + 1} from page {idx + 1}")
                except Exception as e:
                    st.warning(f"⚠️ Could not parse table {table_idx + 1} from page {idx + 1}: {e}")
        
        # Final summary
        if all_dataframes:
            st.success(f"🎉 Extraction complete! Total tables extracted: {len(all_dataframes)} from {len(results)} pages")
        else:
            st.warning("ℹ️ No tables were extracted from any page")
        
        return all_dataframes, markdown_contents
    
    except Exception as e:
        st.error(f"❌ Error parsing document: {e}")
        return [], []

def debug_parse_results(file_path):
    """Debug function to check what parse() returns"""
    try:
        results = parse(file_path)
        st.write("🔍 DEBUG INFORMATION:")
        st.write(f"Number of results: {len(results)}")
        st.write(f"Type of results: {type(results)}")
        
        for i, result in enumerate(results):
            st.write(f"Result {i}: {type(result)}")
            if hasattr(result, 'markdown'):
                st.write(f"  Markdown length: {len(result.markdown)} characters")
                # Show preview of content
                preview = result.markdown[:500] + "..." if len(result.markdown) > 500 else result.markdown
                st.write(f"  Content preview: {preview}")
            else:
                st.write(f"  No markdown attribute found")
                
    except Exception as e:
        st.error(f"Debug error: {e}")

def get_table_download_link(df, filename):
    """Generate a download link for DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV File</a>'
    return href

def save_markdown_to_temp(markdown_content):
    """Save markdown content to a temporary file and return the path"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as tmp_file:
        tmp_file.write(markdown_content)
        return tmp_file.name

def validate_file_size(file, max_size_mb=10):
    """Validate file size doesn't exceed limit"""
    file_size_mb = file.size / (1024 * 1024)  # Convert to MB
    if file_size_mb > max_size_mb:
        return False, file_size_mb
    return True, file_size_mb

def main():
    st.set_page_config(page_title="DESMOND Document Table Extractor", page_icon="📄", layout="wide")
    
    # Custom CSS for green color and styling
    st.markdown("""
    <style>
    .desmond-title {
        color: #00FF00;
        font-weight: bold;
        font-size: 2.5em;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title with your name in green capital letters
    st.markdown('<div class="desmond-title">DESMOND DOCUMENT TABLE & CHECKBOX EXTRACTOR</div>', unsafe_allow_html=True)
    
    st.markdown("Upload PDF, JPEG, or PNG files to extract tables and checkbox information using Agentic Doc Parser")
    
    # Sidebar for additional options
    st.sidebar.title("Options")
    show_markdown = st.sidebar.checkbox("Show Raw Markdown Output", value=False)
    show_all_tables = st.sidebar.checkbox("Show All Tables", value=True)
    show_debug = st.sidebar.checkbox("Show Debug Info", value=False)
    
    # File upload - allow JPEG, PNG, and PDF files
    uploaded_file = st.file_uploader(
        "Choose a file (PDF, JPEG, PNG)", 
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=False,
        help="Upload PDF documents or images (JPEG/PNG) containing tables"
    )
    
    # File size limit (10 MB)
    MAX_FILE_SIZE_MB = 10
    
    if uploaded_file is not None:
        # Validate file size
        is_valid_size, file_size_mb = validate_file_size(uploaded_file, MAX_FILE_SIZE_MB)
        
        if not is_valid_size:
            st.error(f"❌ File size ({file_size_mb:.2f} MB) exceeds the maximum allowed size of {MAX_FILE_SIZE_MB} MB")
            return
        
        # Display file info
        file_type = uploaded_file.type
        st.success(f"✅ File uploaded successfully: {uploaded_file.name}")
        st.write(f"📊 File type: {file_type}")
        st.write(f"📏 File size: {file_size_mb:.2f} MB")
        
        # Create temporary file
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # Parse button - THIS SHOULD BE INSIDE THE MAIN FUNCTION
        if st.button("Extract Tables and Checkboxes", type="primary"):
            with st.spinner(f"Parsing {file_type} and extracting tables..."):
                # Optional: Add debug info
                if show_debug:
                    debug_parse_results(tmp_file_path)
                
                dataframes, markdown_contents = parse_document(tmp_file_path)
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
            # Display results
            if dataframes:
                st.success(f"✅ Successfully extracted {len(dataframes)} tables from {len(markdown_contents)} pages")
                
                # Summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Tables", len(dataframes))
                with col2:
                    st.metric("Total Pages", len(markdown_contents))
                with col3:
                    total_rows = sum(len(df) for df in dataframes)
                    st.metric("Total Rows", total_rows)
                
                # Display tables
                if show_all_tables:
                    st.subheader("📊 Extracted Tables")
                    
                    for i, df in enumerate(dataframes):
                        with st.container():
                            st.markdown(f"**Table {i+1}** (Page {df['source_page'].iloc[0]}, Table {df['table_number'].iloc[0]})")
                            
                            # Display DataFrame
                            display_df = df.drop(['source_page', 'table_number', 'table_id'], axis=1) if all(col in df.columns for col in ['source_page', 'table_number', 'table_id']) else df
                            st.dataframe(display_df, use_container_width=True)
                            
                            # Download button for individual table
                            st.markdown(get_table_download_link(df, f"table_{i+1}.csv"), unsafe_allow_html=True)
                            
                            st.markdown("---")
                
                # Combined data download
                if len(dataframes) > 1:
                    st.subheader("📥 Download All Data")
                    
                    # Combine all dataframes
                    combined_df = pd.concat(dataframes, ignore_index=True)
                    st.markdown(get_table_download_link(combined_df, "all_tables.csv"), unsafe_allow_html=True)
                    
                    # Display combined data preview
                    with st.expander("Preview Combined Data"):
                        st.dataframe(combined_df, use_container_width=True)
            
            else:
                st.warning("⚠️ No tables found in the document.")
                if markdown_contents:
                    st.info("The document was processed successfully but no tabular data was detected.")
            
            # Display raw markdown if requested
            if show_markdown and markdown_contents:
                st.subheader("📝 Raw Markdown Output")
                
                for i, markdown_content in enumerate(markdown_contents):
                    with st.expander(f"Page {i+1} Markdown"):
                        # Create temporary file for markdown content
                        md_file_path = save_markdown_to_temp(markdown_content)
                        
                        # Display content in text area
                        st.text_area(
                            f"Markdown Content - Page {i+1}", 
                            markdown_content, 
                            height=300,
                            key=f"markdown_{i}"
                        )
                        
                        # Provide download button for markdown
                        with open(md_file_path, 'r', encoding='utf-8') as f:
                            st.download_button(
                                label=f"Download Page {i+1} Markdown",
                                data=f.read(),
                                file_name=f"page_{i+1}_content.md",
                                mime="text/markdown",
                                key=f"download_md_{i}"
                            )
                        
                        # Clean up temporary markdown file
                        os.unlink(md_file_path)
        
        else:
            # Clean up temporary file if parsing wasn't initiated
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    else:
        st.info("👆 Please upload a PDF, JPEG, or PNG file to get started")
        
        # Example usage instructions
        with st.expander("ℹ️ How to use this app"):
            st.markdown("""
            ### 📋 Instructions:
            1. **Upload a file** (PDF, JPEG, or PNG) containing tables and/or checkboxes
            2. Click the **"Extract Tables and Checkboxes"** button
            3. View the extracted tables in tabular format
            4. Download individual tables or all data as CSV files
            5. Optionally view the raw markdown output
            
            ### ✅ Supported File Types:
            - **PDF documents** (multi-page support)
            - **JPEG images** (.jpg, .jpeg)
            - **PNG images** (.png)
            
            ### 📏 File Limits:
            - Maximum file size: 10 MB
            - For larger files, consider compressing images or splitting PDFs
            
            ### ⚠️ Important Notes:
            - Ensure your API key is properly configured in the .env file
            - Image quality affects extraction accuracy
            - Complex tables may require additional processing
            """)

if __name__ == "__main__":
    main()