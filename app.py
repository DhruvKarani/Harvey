import re

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json

from LegalDocAnalyser import extract_text, summarize_document, extract_clauses, summarize_clause
from classifier import classify_clause_with_evidence, extract_entities

import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "Blah")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    gemini_model = None
    print("[WARNING] GEMINI_API_KEY not set. Gemini mode will fall back to local.")


app = FastAPI(title="Harvey - Legal Document Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CLAUSE_DB_PATH = "clauses_db.json"

last_doc = {"text": "", "clauses": [], "typed_clauses": []}


# ---------------------------------------------------------------------------
# Pydantic model for /chat
# ---------------------------------------------------------------------------
# use_gemini: bool sent by the frontend based on user's privacy choice
# Defaults to False — local mode is the safer default
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    use_gemini: bool = False


def label_clauses(clauses: list) -> list:
    labeled = []
    for clause in clauses:
        classification = classify_clause_with_evidence(clause)
        entities = extract_entities(clause)
        labeled.append({
            "text": clause,
            "type": classification["type"],
            "matched_text": classification["matched_text"],
            "entities": entities
        })
    return labeled


def save_clauses_to_db(typed_clauses: list):
    try:
        if os.path.exists(CLAUSE_DB_PATH):
            with open(CLAUSE_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
        else:
            db = []
        db.extend(typed_clauses)
        with open(CLAUSE_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[DEBUG] Could not save clauses to db:", e)


# ---------------------------------------------------------------------------
# STEP 1: Keyword search — finds most relevant clause
# ---------------------------------------------------------------------------
# Splits question into words (>2 chars to filter noise like "is", "of", "a")
# Counts how many question words appear in each clause
# Returns the clause with highest overlap score
# This runs locally — no external calls, no privacy concern
# ---------------------------------------------------------------------------
def find_best_clause(question: str, typed_clauses: list) -> dict | None:
    if not typed_clauses:
        return None

    question_words = set(
    re.sub(r'[^a-z]', '', word.lower())  # remove all non-letter characters
    for word in question.split()
    if len(word) > 2
)

    print(f"[DEBUG] Question words: {question_words}")  # ADD THIS

    best_clause = None
    best_score = -1

    for clause in typed_clauses:
        clause_text_lower = clause["text"].lower()
        score = sum(1 for word in question_words if word in clause_text_lower)
        print(f"[DEBUG] Score {score}: {clause['text'][:60]}")  # ADD THIS
        if score > best_score:
            best_score = score
            best_clause = clause

    return best_clause if best_score > 0 else typed_clauses[0]

    best_clause = None
    best_score = -1

    for clause in typed_clauses:
        clause_text_lower = clause["text"].lower()
        score = sum(1 for word in question_words if word in clause_text_lower)
        if score > best_score:
            best_score = score
            best_clause = clause

    return best_clause if best_score > 0 else typed_clauses[0]


# ---------------------------------------------------------------------------
# STEP 2A: Gemini answer — sends clause text to Google's API
# ---------------------------------------------------------------------------
# Only called when user explicitly opts in via use_gemini=True
# Prompt constrains Gemini to answer using only the provided clause
# Falls back to local answer if API call fails
# ---------------------------------------------------------------------------
def ask_gemini(question: str, context_clause: str) -> str:
    if not gemini_model:
        return f"Gemini is not configured. Most relevant clause:\n\n{context_clause}"

    prompt = f"""You are a legal document assistant.
Answer the question using ONLY the clause text provided below.
If the clause does not contain enough information to answer, say so clearly.

Clause from the document:
\"\"\"
{context_clause}
\"\"\"

User's question: {question}

Answer clearly and concisely in plain English."""

    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[DEBUG] Gemini call failed: {e}")
        return f"Gemini unavailable. Most relevant clause:\n\n{context_clause}"


# ---------------------------------------------------------------------------
# STEP 2B: Local answer — returns matched clause directly
# ---------------------------------------------------------------------------
# No external calls. The clause text IS the answer.
# Simple but honest — and fully private.
# ---------------------------------------------------------------------------
def answer_locally(context_clause: str) -> str:
    return f"Most relevant clause found in your document:\n\n{context_clause}"


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large (max 10MB).")

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    text = extract_text(filepath)
    summary = summarize_document(text)
    clauses = extract_clauses(text)
    typed_clauses = label_clauses(clauses)

    last_doc["text"] = text
    last_doc["clauses"] = clauses
    last_doc["typed_clauses"] = typed_clauses

    save_clauses_to_db(typed_clauses)

    clause_outputs = []
    for c in typed_clauses:
        name = c["type"].replace("_", " ").title() if c["type"] != "unknown" else c["text"].split(":")[0][:30]
        desc = summarize_clause(c["text"])
        clause_outputs.append({
            "name": name,
            "summary": desc,
            "matched_text": c["matched_text"],
            "entities": c["entities"]
        })

    return {
        "summary": summary,
        "clauses": clause_outputs,
        "typed_clauses": typed_clauses
    }


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------
# Step 1 (always): keyword search finds the best clause — local, private
# Step 2 (branches on use_gemini flag):
#   True  → send clause to Gemini, get natural language answer
#   False → return the clause directly, nothing leaves the server
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat(body: ChatRequest):
    question = body.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not last_doc["typed_clauses"]:
        return {"answer": "Please upload a document first before asking questions."}

    # Step 1: always runs locally
    best = find_best_clause(question, last_doc["typed_clauses"])
    print(f"[DEBUG] Best clause: {best['type']} — score matched for '{question}'")

    # Step 2: branch on user's privacy choice
    if body.use_gemini:
        answer = ask_gemini(question, best["text"])
        mode = "gemini"
    else:
        answer = answer_locally(best["text"])
        mode = "local"

    return {
        "answer": answer,
        "mode": mode,   # tells frontend which mode was actually used
        "source_clause_type": best["type"].replace("_", " ").title(),
        "source_clause_text": best["text"]
    }