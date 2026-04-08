FILE                  OWNS
-------------------------------------------------
LegalDocAnalyser.py   Text extraction, clause segmentation, summarization
classifier.py         SpaCy Matcher patterns, NER, classify/extract functions
app.py                FastAPI routes, orchestration, Gemini/local Q&A logic
frontend.py           Streamlit UI, user input, displays results

KEY FUNCTIONS
-------------------------------------------------
extract_text()           — PyPDF2 → OCR fallback
extract_clauses()        — regex segmentation, 3 fallback strategies
classify_clause_with_evidence()  — SpaCy Matcher, returns type + matched word
extract_entities()       — SpaCy NER, returns persons/orgs/dates/locations
find_best_clause()       — keyword overlap search
ask_gemini()             — RAG generation step