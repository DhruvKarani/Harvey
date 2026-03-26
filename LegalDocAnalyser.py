import os
import PyPDF2
from pdf2image import convert_from_path
import pytesseract
import re
import tkinter as tk
from tkinter import filedialog, scrolledtext

# Set the path to tesseract.exe if not in PATH (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Set the path to Poppler's bin directory for pdf2image (adjust if needed)
poppler_path = r'C:\Users\dhruv\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin'  # <-- Change this to your actual Poppler bin path
os.environ["PATH"] += os.pathsep + poppler_path

try:
    print('[DEBUG] Tesseract version:', pytesseract.get_tesseract_version())
except Exception as e:
    print('[DEBUG] Could not get Tesseract version:', e)

try:
    from pdf2image.exceptions import PDFInfoNotInstalledError
except ImportError:
    PDFInfoNotInstalledError = Exception

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
            if text.strip():
                print("[DEBUG] Direct PDF extraction succeeded. Length:", len(text))
                return text
            else:
                print("[DEBUG] Direct PDF extraction returned empty text.")
        except Exception as e:
            print(f"[DEBUG] Direct PDF extraction failed: {e}")
        try:
            print("[DEBUG] Attempting OCR extraction with pdf2image and pytesseract...")
            images = convert_from_path(filepath)
            print(f"[DEBUG] Number of images/pages detected: {len(images)}")
            ocr_text = ""
            for idx, img in enumerate(images):
                page_ocr = pytesseract.image_to_string(img)
                print(f"[DEBUG] OCR text length for page {idx+1}: {len(page_ocr)}")
                ocr_text += page_ocr
            if not ocr_text.strip():
                print("[DEBUG] OCR extraction returned empty text. Check if Tesseract is installed and in PATH.")
            else:
                print(f"[DEBUG] OCR extraction succeeded. Total OCR text length: {len(ocr_text)}")
            return ocr_text
        except PDFInfoNotInstalledError as e:
            print("[DEBUG] Poppler is not installed or not in PATH. Please install Poppler and add it to your PATH.")
            return ""
        except Exception as e:
            print(f"[DEBUG] OCR extraction failed: {e}")
            return ""
    else:
        print("[DEBUG] Unsupported file type.")
        return ""

def extract_clauses(text):
    import re
    # Try to split on numbered clauses (e.g., 1. ... 2. ...)
    pattern = r'(?:^|\n)(\d+\.\s)'
    splits = [m.start() for m in re.finditer(pattern, text)]
    if len(splits) > 1:
        clauses = []
        for i in range(len(splits)):
            start = splits[i]
            end = splits[i+1] if i+1 < len(splits) else len(text)
            clause = text[start:end].strip()
            if clause:
                clauses.append(clause)
        print(f"[DEBUG] Extracted {len(clauses)} clauses (numbered split).")
        return clauses
    # Fallback: regex/paragraph splitting
    pattern = r'(?:^|\n)([A-Z][A-Za-z\s]+?\s+Clause:|Section\s+\d+:|Article\s+\d+:|[A-Z][A-Za-z\s]+:|\d+\.\s+)'  # Match clause headings
    splits = [m.start() for m in re.finditer(pattern, text)]
    clauses = []
    for i in range(len(splits)):
        start = splits[i]
        end = splits[i+1] if i+1 < len(splits) else len(text)
        clause = text[start:end].strip()
        if len(clause) > 40:
            clauses.append(clause)
    if clauses:
        print(f"[DEBUG] Extracted {len(clauses)} clauses (heading split).")
        return clauses
    # fallback: split by paragraphs
    paras = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 40]
    print(f"[DEBUG] Extracted {len(paras)} clauses (paragraph split).")
    return paras

def summarize_clause(clause):
    sentences = re.split(r'(?<=[.!?]) +', clause)
    # Use first 2 sentences for a more meaningful summary
    summary = ' '.join(sentences[:2]) if sentences else clause
    if len(summary.split()) > 50:
        summary = ' '.join(summary.split()[:50]) + '...'
    return summary

def summarize_document(text):
    sentences = re.split(r'(?<=[.!?]) +', text)
    # Use first 5 sentences for a longer summary
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