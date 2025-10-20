import os
import re
import streamlit as st
import pandas as pd
from io import StringIO
from pdf2image import convert_from_path
from dotenv import load_dotenv
from agentic_doc.parse import parse
from groq import Groq

# ------------------------------
# CONFIG
# ------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LANDING_API_KEY = os.getenv("LANDING_API_KEY")
os.environ["VISION_AGENT_API_KEY"] = LANDING_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

try:
    client = Groq(api_key=GROQ_API_KEY)
except Exception:
    client = None

OUTPUT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)
st.set_page_config(page_title="Desmond Agentic Document Extraction", layout="wide")

# ------------------------------
# SESSION STATE
# ------------------------------
if "files" not in st.session_state:
    st.session_state["files"] = []
if "active_file" not in st.session_state:
    st.session_state["active_file"] = None
if "parsed_results" not in st.session_state:
    st.session_state["parsed_results"] = []
if "images" not in st.session_state:
    st.session_state["images"] = []
if "all_tables" not in st.session_state:
    st.session_state["all_tables"] = []
if "all_forms" not in st.session_state:
    st.session_state["all_forms"] = []
if "all_checkboxes" not in st.session_state:
    st.session_state["all_checkboxes"] = []
if "text_blocks" not in st.session_state:
    st.session_state["text_blocks"] = []
if "current_page" not in st.session_state:
    st.session_state["current_page"] = 1

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------
def ensure_parsed(file_path):
    """Parse file once and populate session state, including checkboxes."""
    if st.session_state.get("parsed_results") and \
       st.session_state.get("uploaded_file_name") == os.path.basename(file_path):
        return

    results = parse(file_path)
    images = convert_from_path(file_path, dpi=150)
    st.session_state["parsed_results"] = results
    st.session_state["images"] = images

    tables, forms, checkboxes, text_blocks = [], [], [], []

    for idx, result in enumerate(results):
        page_num = idx + 1
        # Extract tables
        tables_found = re.findall(r"<table.*?>.*?</table>", result.markdown or "", re.DOTALL)
        for html in tables_found:
            try:
                dfs = pd.read_html(StringIO(html))
                for df in dfs:
                    df["source_page"] = page_num
                    tables.append(df)
                    text_blocks.append({"text": df.to_string(index=False), "source_page": page_num})
            except:
                pass

        # Extract form fields
        if hasattr(result, "fields") and result.fields:
            for field in result.fields:
                forms.append({
                    "field_name": getattr(field, "name", None),
                    "field_value": getattr(field, "value", None),
                    "source_page": page_num
                })
                text_blocks.append({"text": f"{field.name}: {field.value}", "source_page": page_num})

        # Extract checkboxes
        checkbox_matches = re.findall(r"option\s*[:\-]?\s*\[([xX ])\]\s*(.*)", result.markdown or "")
        for val, label in checkbox_matches:
            checked = val.lower() == "x"
            checkboxes.append({
                "label": label.strip(),
                "checked": checked,
                "source_page": page_num
            })
            text_blocks.append({"text": f"{label.strip()}: {'Checked' if checked else 'Unchecked'}", "source_page": page_num})

        # Include other text
        if hasattr(result, "markdown") and result.markdown:
            text_blocks.append({"text": result.markdown, "source_page": page_num})

    st.session_state["all_tables"] = tables
    st.session_state["all_forms"] = forms
    st.session_state["all_checkboxes"] = checkboxes
    st.session_state["text_blocks"] = text_blocks
    st.session_state["uploaded_file_name"] = os.path.basename(file_path)

# ------------------------------
# HEADER
# ------------------------------
st.markdown("""
<div style='background-color:#e6f7e6; padding: 20px; border-radius: 10px;'>
    <h1 style='color: #006400; margin-bottom:5px; text-transform:uppercase;'>
        DESMOND AGENTIC: EXTRACT DATA FROM FORMS, PDFS & CHECKBOXES
    </h1>
    <p style='font-size:18px; color:#004d00; margin-top:0px;'>
        A cutting-edge Visual AI platform for parsing, extracting, and intelligently answering questions from documents.
    </p>
    <h3 style='color: #008000; margin-top:10px;'>Upload PDFs and checkboxes for analysis</h3>
</div>
<hr>
""", unsafe_allow_html=True)

# ------------------------------
# LAYOUT
# ------------------------------
left, center, right = st.columns([1.2, 2.5, 2])

# ---- LEFT PANEL ----
with left:
    st.subheader("Files")
    uploaded = st.file_uploader("Upload JPG, PNG, or PDF", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded:
        file_name = uploaded.name
        if file_name not in [f["name"] for f in st.session_state["files"]]:
            path = os.path.join(OUTPUT_DIR, file_name)
            with open(path, "wb") as f:
                f.write(uploaded.read())
            st.session_state["files"].append({"name": file_name, "path": path})
            st.success(f"Uploaded {file_name}")
        else:
            st.warning(f"{file_name} is already uploaded.")

    st.markdown("**Your Files**")
    for idx, fmeta in enumerate(st.session_state["files"]):
        name = fmeta["name"]
        if st.button(f"{idx+1}. {name}", key=f"filebtn_{idx}"):
            st.session_state["active_file"] = fmeta["path"]

    if st.session_state["active_file"]:
        st.markdown(f"**Active:** {os.path.basename(st.session_state['active_file'])}")
        if st.button("Parse"):
            ensure_parsed(st.session_state["active_file"])
            st.success("Parsed successfully.")
        if st.button("Clear Selection"):
            st.session_state["active_file"] = None
            st.session_state["current_page"] = 1
            st.session_state["parsed_results"] = []
            st.session_state["all_tables"] = []
            st.session_state["all_forms"] = []
            st.session_state["all_checkboxes"] = []
            st.session_state["text_blocks"] = []

# ---- CENTER PANEL ----
with center:
    st.subheader("Preview")
    if not st.session_state["active_file"]:
        st.info("Upload and parse a document first.")
    else:
        ensure_parsed(st.session_state["active_file"])
        images = st.session_state.get("images") or []
        if images:
            n_pages = len(images)
            page = st.number_input("Page", min_value=1, max_value=n_pages,
                                   value=st.session_state.get("current_page", 1))
            st.session_state["current_page"] = page
            st.image(images[page-1], use_container_width=True)

# ---- RIGHT PANEL ----
with right:
    st.subheader("Extracted Data")
    if st.session_state.get("all_tables"):
        for i, df in enumerate(st.session_state["all_tables"]):
            st.markdown(f"**Table {i+1} (Page {df['source_page'].iloc[0]})**")
            st.dataframe(df, use_container_width=True)

    if st.session_state.get("all_forms"):
        st.markdown("**Form Fields**")
        st.dataframe(pd.DataFrame(st.session_state["all_forms"]), use_container_width=True)

    if st.session_state.get("all_checkboxes"):
        st.markdown("**Checkboxes**")
        for cb in st.session_state["all_checkboxes"]:
            status = "✅" if cb["checked"] else "⬜"
            st.write(f"{status} {cb['label']} (Page {cb['source_page']})")

    st.markdown("---")
    st.subheader("Chat")
    question = st.text_input("Ask a question about this document:")
    if st.button("Ask"):
        if not st.session_state.get("text_blocks"):
            st.warning("Please parse the document first.")
        else:
            # Remove duplicate lines and clean text
            context = []
            seen = set()
            for tb in st.session_state["text_blocks"]:
                clean_text = re.sub(r'\s+', ' ', tb["text"]).strip()
                if clean_text and clean_text not in seen:
                    context.append(clean_text)
                    seen.add(clean_text)
            full_context = "\n".join(context)

            prompt = f"Answer the question based on the context below. Provide concise and accurate answers.\nContext:\n{full_context}\nQuestion: {question}\nAnswer:"

            answer_text = ""
            if client:
                try:
                    completion = client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        max_completion_tokens=1024,
                        stream=False
                    )
                    answer_text = completion.choices[0].message.content
                except Exception as e:
                    answer_text = f"Error calling Groq: {e}"
            else:
                answer_text = "Groq client not initialized. Cannot answer questions."

            st.markdown("**Answer:**")
            st.write(answer_text)
