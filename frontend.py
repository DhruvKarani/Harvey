import streamlit as st
import requests
import os

st.set_page_config(page_title="Harvey", layout="centered")
st.title("Harvey")
st.write("Upload your legal document (PDF) for instant clause extraction, smart summaries, and Q&A.")

backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# File upload + analysis
# ---------------------------------------------------------------------------
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
                    st.write(f"**Type:** {typed['type'].replace('_', ' ').title()}")
                    st.write(f"**Summary:** {clause['summary']}")

                    if clause.get("matched_text"):
                        st.write(f"**Matched on:** `{clause['matched_text']}`")

                    entities = clause.get("entities", {})
                    has_entities = any(entities.get(k) for k in ["persons", "orgs", "dates", "locations"])
                    if has_entities:
                        st.write("**Entities found:**")
                        if entities.get("persons"):
                            st.write(f"- 👤 People: {', '.join(entities['persons'])}")
                        if entities.get("orgs"):
                            st.write(f"- 🏢 Organizations: {', '.join(entities['orgs'])}")
                        if entities.get("dates"):
                            st.write(f"- 📅 Dates: {', '.join(entities['dates'])}")
                        if entities.get("locations"):
                            st.write(f"- 📍 Locations: {', '.join(entities['locations'])}")

                    st.write(f"**Full Text:** {typed['text']}")
        else:
            st.error(f"Error: {response.text}")

# ---------------------------------------------------------------------------
# Q&A Section
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Ask a question about your document")

# ---------------------------------------------------------------------------
# Privacy mode toggle
# ---------------------------------------------------------------------------
# Two modes:
#   Gemini  — sends clause text to Google's API, better natural language answer
#   Local   — keyword search only, nothing leaves your machine, returns raw clause
#
# The user picks. We pass their choice to the backend via the request body.
# ---------------------------------------------------------------------------
qa_mode = st.radio(
    "Answer mode:",
    options=["🤖 Gemini (better answers)", "🔒 Local only (privacy safe)"],
    index=1,  # default to Local — safer choice
    horizontal=True
)

# Show disclaimer only when Gemini is selected
if "Gemini" in qa_mode:
    st.warning(
        "⚠️ **Privacy notice:** Your document text will be sent to Google Gemini API to generate the answer. "
        "Do not use this mode for confidential or sensitive legal documents."
    )
else:
    st.info(
        "🔒 **Local mode:** Your document never leaves your machine. "
        "The answer is the most relevant clause found by keyword search."
    )

question = st.text_input("Type your question and press Enter")

if st.button("Ask") and question:
    with st.spinner("Searching document..."):

        # Tell the backend which mode the user chose
        use_gemini = "Gemini" in qa_mode

        resp = requests.post(
            f"{backend_url}/chat",
            json={"question": question, "use_gemini": use_gemini}
        )

        if resp.ok:
            result = resp.json()

            st.write("**Answer:**")
            st.write(result.get("answer", "No answer received."))

            # Always show the source clause — transparency in both modes
            if result.get("source_clause_type"):
                with st.expander(f"📄 Source: {result['source_clause_type']} clause"):
                    st.write(result.get("source_clause_text", ""))
        else:
            st.error(f"Error: {resp.text}")