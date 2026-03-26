# Harvey

> *"I don't have dreams, I have goals."* — Harvey Specter

Harvey is an AI-powered legal document analyzer. Named after the sharpest closer in New York — because your contracts deserve the same ruthless attention to detail.

Upload a legal document. Harvey reads it, extracts every clause, classifies it, summarizes the intent in plain English, and lets you interrogate it like a deposition.

---

## What Harvey does

- **Clause extraction** — identifies and isolates individual legal clauses from any document
- **Clause classification** — categorizes clauses (confidentiality, indemnity, termination, dispute resolution, etc.) using ML + LegalBERT
- **Plain-English summarization** — translates legal jargon into what it actually means
- **OCR support** — handles scanned documents and image-based PDFs via Tesseract
- **Document Q&A** — ask Harvey directly: *"Is there a termination clause?"*, *"Who bears liability?"*, *"Any mention of arbitration?"*

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![SpaCy](https://img.shields.io/badge/SpaCy-09A3D5?style=flat-square&logoColor=white)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)
![Tesseract](https://img.shields.io/badge/Tesseract_OCR-4285F4?style=flat-square&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)

| Component | Technology |
|---|---|
| Clause classification | Scikit-learn + LegalBERT |
| Named Entity Recognition | SpaCy |
| OCR (scanned docs) | PyTesseract |
| PDF parsing | PyMuPDF / PDFMiner |
| Frontend | HTML · CSS · JavaScript |
| Backend | Python + Flask |

---

## Getting Started

```bash
git clone https://github.com/DhruvKarani/Harvey.git
cd Harvey
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000` in your browser.

---

## Supported Input Formats

- PDF (text-based)
- PDF (scanned / image-based) — via OCR
- TXT files

---

## Project Structure

```
Harvey/
│
├── app.py                  # Flask backend
├── LegalDocAnalyser.py     # Core NLP pipeline
├── clauses_db.json         # Clause classification database
├── HomePage.html           # Frontend UI
├── Home.css                # Styling
├── Homie.js                # Frontend logic
├── data/                   # Sample legal documents
└── uploads/                # User-uploaded files (gitignored)
```

---

## Author

**Dhruv Karani** · [LinkedIn](https://www.linkedin.com/in/dhruv-karani-06a03229a/)

---

*Harvey doesn't lose. Neither should you.*
