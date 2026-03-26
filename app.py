
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
from LegalDocAnalyser import extract_text, summarize_document, extract_clauses, summarize_clause


app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CLAUSE_DB_PATH = 'clauses_db.json'

# Clause type mapping
CLAUSE_TYPES = {
    'payment': ['payment', 'fee', 'remuneration', 'compensation', 'amount'],
    'confidentiality': ['confidential', 'non-disclosure', 'privacy', 'secret'],
    'termination': ['terminate', 'termination', 'end', 'expiry', 'cancel'],
    'liability': ['liability', 'liable', 'responsibility', 'indemnify', 'indemnification'],
    'governing law': ['governing law', 'jurisdiction', 'court', 'venue'],
    'force majeure': ['force majeure', 'act of god', 'unforeseeable'],
    'intellectual property': ['intellectual property', 'ip', 'copyright', 'patent', 'trademark'],
    'dispute resolution': ['dispute', 'arbitration', 'mediation', 'resolve'],
    'assignment': ['assign', 'assignment', 'transfer'],
    'notice': ['notice', 'notify', 'notification'],
    # Add more as needed
}

# Store last uploaded document's text and clauses for chat reference
last_doc = {'text': '', 'clauses': [], 'typed_clauses': []}

def save_clauses_to_db(typed_clauses):
    try:
        if os.path.exists(CLAUSE_DB_PATH):
            with open(CLAUSE_DB_PATH, 'r', encoding='utf-8') as f:
                db = json.load(f)
        else:
            db = []
        db.extend(typed_clauses)
        with open(CLAUSE_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('[DEBUG] Could not save clauses to db:', e)

def label_clauses(clauses):
    labeled = []
    for clause in clauses:
        found_type = None
        # Try to detect explicit clause label (e.g., "Severability Clause:")
        import re
        match = re.match(r'([A-Za-z ]+?)\s*clause\b', clause, re.IGNORECASE)
        if match:
            found_type = match.group(1).strip().lower()
            if found_type not in CLAUSE_TYPES:
                CLAUSE_TYPES[found_type] = [found_type]
        if not found_type:
            for ctype, keywords in CLAUSE_TYPES.items():
                for kw in keywords:
                    if kw in clause.lower():
                        found_type = ctype
                        break
                if found_type:
                    break
        labeled.append({'text': clause, 'type': found_type or 'unknown'})
    return labeled

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print('[DEBUG] /analyze endpoint called')
        if 'file' not in request.files:
            print('[DEBUG] No file part in request.files')
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        print(f'[DEBUG] Received file: {file.filename}')
        # Backend file validation
        if not file.filename.lower().endswith('.pdf'):
            print('[DEBUG] File is not a PDF')
            return jsonify({'error': 'Only PDF files are allowed.'}), 400
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)
        print(f'[DEBUG] File size: {size} bytes')
        if size > 10 * 1024 * 1024:
            print('[DEBUG] File is too large')
            return jsonify({'error': 'File is too large (max 10MB).'}), 400
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        print(f'[DEBUG] File saved to: {filepath}')
        text = extract_text(filepath)
        print(f'[DEBUG] Extracted text length: {len(text)}')
        summary = summarize_document(text)
        clauses = extract_clauses(text)
        print(f'[DEBUG] Extracted {len(clauses)} clauses')
        for idx, clause in enumerate(clauses):
            print(f'[DEBUG] Clause {idx+1}: {repr(clause)[:200]}')
        typed_clauses = label_clauses(clauses)
        # Store for chat
        last_doc['text'] = text
        last_doc['clauses'] = clauses
        last_doc['typed_clauses'] = typed_clauses
        save_clauses_to_db(typed_clauses)
        # Prepare clause output: show clause name (type or first line) and a one-line summary
        clause_outputs = []
        for c in typed_clauses:
            name = c['type'].title() if c['type'] != 'unknown' else c['text'].split(':')[0][:30]
            desc = summarize_clause(c['text'])
            clause_outputs.append({'name': name, 'summary': desc})
        print('[DEBUG] Returning analysis result')
        return jsonify({
            'summary': summary,
            'clauses': clause_outputs,
            'typed_clauses': typed_clauses
        })
    except Exception as e:
        import traceback
        print('[ERROR] Exception in /analyze:', e)
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = data.get('question', '').strip()
    # Always return the custom dummy answer
    return jsonify({'answer': "Since the clause represent confidentiality we cannot answer these questions but we may show the text in your Document that says this. Thank You"})

if __name__ == '__main__':
    app.run(debug=True)
