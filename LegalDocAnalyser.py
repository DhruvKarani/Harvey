import os
import PyPDF2
from pdf2image import convert_from_path
import pytesseract
import re
import tkinter as tk
from tkinter import filedialog, scrolledtext

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

poppler_path = r'C:\Users\dhruv\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin'
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


def process_file(filepath, output_box):
    output_box.delete(1.0, tk.END)
    if not filepath:
        output_box.insert(tk.END, "No file selected.\n")
        return
    output_box.insert(tk.END, f"Processing file: {filepath}\n")
    text = extract_text(filepath)
    if not text.strip():
        output_box.insert(tk.END, "No text could be extracted from this file.\n")
        return
    output_box.insert(tk.END, "\n--- Document Summary ---\n")
    output_box.insert(tk.END, summarize_document(text) + "\n")
    clauses = extract_clauses(text)
    if not clauses:
        output_box.insert(tk.END, "No clauses could be detected.\n")
    else:
        output_box.insert(tk.END, f"Found {len(clauses)} clauses. Summaries:\n")
        for i, clause in enumerate(clauses, 1):
            output_box.insert(tk.END, f"\nClause {i}:\n")
            output_box.insert(tk.END, "Original: " + clause + "\n")
            output_box.insert(tk.END, "Summary: " + summarize_clause(clause) + "\n")


def upload_and_process(output_box):
    filepath = filedialog.askopenfilename(
        title="Select a legal document",
        filetypes=[('PDF files', '*.pdf'), ('Text files', '*.txt'), ('All files', '*.*')]
    )
    if filepath:
        process_file(filepath, output_box)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Legal Document Analyzer")
    root.geometry("800x600")

    upload_btn = tk.Button(root, text="Upload File", command=lambda: upload_and_process(output_box))
    upload_btn.pack(pady=10)

    output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=35)
    output_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    root.mainloop()