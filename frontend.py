import streamlit as st
import requests
import os

st.set_page_config(page_title="Harvey", layout="centered")
st.title("Harvey")
st.write("Upload your legal document (PDF) for instant clause extraction, smart summaries, and Q&A.")

backend_url = os.environ.get("BACKEND_URL", "http://localhost:5000")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("Analyzing document..."):
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        response = requests.post(f"{backend_url}/analyze", files=files)
        if response.ok:
            data = response.json()
            st.subheader("Summary")
            st.write(data.get("summary", "No summary available."))
            st.subheader("Clauses")
            for clause, typed in zip(data.get("clauses", []), data.get("typed_clauses", [])):
                with st.expander(clause["name"]):
                    st.write(f"**Summary:** {clause['summary']}")
                    st.write(f"**Full Text:** {typed['text']}")
        else:
            st.error(f"Error: {response.text}")

st.markdown("---")
st.subheader("Ask a question about your document")
question = st.text_input("Type your question and press Enter")
if st.button("Ask") and question:
    resp = requests.post(f"{backend_url}/chat", json={"question": question})
    if resp.ok:
        st.write(resp.json().get("answer", "No answer received."))
    else:
        st.error(f"Error: {resp.text}")
