import os
import PyPDF2
from pdf2image import convert_from_path
import pytesseract
import re

# On Linux (Render, most servers), tesseract and poppler are installed as
# system packages and are already on PATH, so pytesseract/pdf2image find them
# automatically. We only override the path when TESSERACT_CMD or POPPLER_PATH
# env vars are explicitly set (e.g. for local Windows dev).
if os.environ.get("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]

poppler_path = os.environ.get("POPPLER_PATH")
if poppler_path:
    os.environ["PATH"] += os.pathsep + poppler_path

try:
    print('[DEBUG] Tesseract version:', pytesseract.get_tesseract_version())
except Exception as e:
    print('[DEBUG] Could not get Tesseract version:', e)

try:
    from pdf2image.exceptions import PDFInfoNotInstalledError
except ImportError:
    PDFInfoNotInstalledError = Exception


def clean_text(text):
    # ---------------------------------------------------------------------------
    # Collapse all whitespace — newlines, tabs, multiple spaces — into one space.
    # PyPDF2 often inserts \n after every word when parsing PDFs.
    # We do this ONCE after all pages are collected, not inside the page loop.
    # ---------------------------------------------------------------------------
    return ' '.join(text.split())


def extract_text(filepath):
    if filepath.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    elif filepath.endswith('.pdf'):
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
                        # NOTE: do NOT clean inside this loop
                        # cleaning must happen after all pages are joined

            if text.strip():
                text = clean_text(text)  # clean ONCE after all pages collected
                print("[DEBUG] Direct PDF extraction succeeded. Length:", len(text))
                return text
            else:
                print("[DEBUG] Direct PDF extraction returned empty text.")

        except Exception as e:
            print(f"[DEBUG] Direct PDF extraction failed: {e}")

        try:
            print("[DEBUG] Attempting OCR extraction...")
            images = convert_from_path(filepath)
            ocr_text = ""
            for idx, img in enumerate(images):
                page_ocr = pytesseract.image_to_string(img)
                print(f"[DEBUG] OCR page {idx+1} length: {len(page_ocr)}")
                ocr_text += page_ocr

            if ocr_text.strip():
                ocr_text = clean_text(ocr_text)  # clean OCR output too
                print(f"[DEBUG] OCR succeeded. Length: {len(ocr_text)}")
            else:
                print("[DEBUG] OCR returned empty text.")
            return ocr_text

        except PDFInfoNotInstalledError:
            print("[DEBUG] Poppler not installed or not in PATH.")
            return ""
        except Exception as e:
            print(f"[DEBUG] OCR failed: {e}")
            return ""
    else:
        print("[DEBUG] Unsupported file type.")
        return ""


def extract_clauses(text):
    # ---------------------------------------------------------------------------
    # Since clean_text() removed all newlines, we can no longer split on \n.
    # We now split on numbered clause patterns that appear inline.
    # e.g. "...end of clause 1. 2. Payment The client agrees..."
    #
    # Strategy 1: numbered clauses — "1. " "2. " etc appearing mid-text
    # Strategy 2: heading keywords — "Section X:" "Article X:"
    # Strategy 3: sentence splitting fallback
    # ---------------------------------------------------------------------------

    # Strategy 1: numbered clauses
    # re.split keeps the delimiter when wrapped in a capturing group
    parts = re.split(r'(\d+\.\s+[A-Z])', text)
    if len(parts) > 3:
        # re.split with capturing group gives: [before, delim, content, delim, content...]
        # rejoin delimiter with its content
        clauses = []
        i = 1
        while i < len(parts) - 1:
            clause = parts[i] + parts[i+1]
            clause = clause.strip()
            if len(clause) > 40:
                clauses.append(clause)
            i += 2
        if clauses:
            print(f"[DEBUG] Extracted {len(clauses)} clauses (numbered split).")
            return clauses

    # Strategy 2: heading keywords
    parts = re.split(r'((?:Section|Article|Clause)\s+\d+[:\.])', text, flags=re.IGNORECASE)
    if len(parts) > 3:
        clauses = []
        i = 1
        while i < len(parts) - 1:
            clause = parts[i] + parts[i+1]
            clause = clause.strip()
            if len(clause) > 40:
                clauses.append(clause)
            i += 2
        if clauses:
            print(f"[DEBUG] Extracted {len(clauses)} clauses (heading split).")
            return clauses

    # Strategy 3: sentence-based fallback — group every 5 sentences into a clause
    sentences = re.split(r'(?<=[.!?]) +', text)
    clauses = []
    for i in range(0, len(sentences), 5):
        chunk = ' '.join(sentences[i:i+5]).strip()
        if len(chunk) > 40:
            clauses.append(chunk)
    print(f"[DEBUG] Extracted {len(clauses)} clauses (sentence fallback).")
    return clauses


def summarize_clause(clause):
    sentences = re.split(r'(?<=[.!?]) +', clause)
    summary = ' '.join(sentences[:2]) if sentences else clause
    if len(summary.split()) > 50:
        summary = ' '.join(summary.split()[:50]) + '...'
    return summary


def summarize_document(text):
    sentences = re.split(r'(?<=[.!?]) +', text)
    summary = ' '.join(sentences[:5])
    if len(summary.split()) > 120:
        summary = ' '.join(summary.split()[:120]) + '...'
    return summary


# NOTE: The original version of this file included a Tkinter desktop GUI
# (process_file / upload_and_process / an `if __name__ == '__main__'` block
# that launched a Tk window). That GUI is not used by the web app — app.py
# and frontend.py call extract_text/summarize_document/extract_clauses/
# summarize_clause directly over HTTP — so it has been removed along with
# the `tkinter` import. Tkinter isn't installed in minimal Linux server
# images, so keeping that import would crash the backend on startup.