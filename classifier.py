import spacy
from spacy.matcher import Matcher

# ---------------------------------------------------------------------------
# STEP 1: Load SpaCy's English model
# ---------------------------------------------------------------------------
# en_core_web_sm does two things we use:
#   1. Tokenization — breaks text into words (used by Matcher)
#   2. NER — labels named entities like people, orgs, dates (used by extract_entities)
# Loaded once at module level so it's not reloaded on every function call.
# ---------------------------------------------------------------------------
nlp = spacy.load("en_core_web_sm")


# ---------------------------------------------------------------------------
# STEP 2: Clause classification patterns
# ---------------------------------------------------------------------------
# Each key is a clause type name.
# Each value is a list of patterns (OR logic — any one match is enough).
# Each pattern is a list of token dicts (AND logic — all must match in order).
#
# "LOWER" = match lowercase form of token   → exact word, case-insensitive
# "LEMMA" = match base/root form of token   → catches all inflections
#
# Why not bare "ip"?
# "ip" alone is too short and ambiguous. It appears inside words like
# "partnership" as a substring in naive matching. With the Matcher it won't
# false-positive on substrings (tokens are whole words), but it could still
# match unrelated uses of "IP" (e.g. IP address). So we require the full
# phrase "intellectual property" instead.
# ---------------------------------------------------------------------------

CLAUSE_PATTERNS = {

    "payment": [
        [{"LEMMA": "pay"}],                                        # pay, pays, paid, payment
        [{"LOWER": "fee"}],
        [{"LOWER": "invoice"}],
        [{"LOWER": "compensation"}],
        [{"LOWER": "remuneration"}],
    ],

    "confidentiality": [
        [{"LOWER": "confidential"}],
        [{"LOWER": "non-disclosure"}],
        [{"LOWER": "nda"}],
        [{"LOWER": "secret"}],
        [{"LOWER": "privacy"}],
    ],

    "termination": [
        [{"LEMMA": "terminate"}],                                  # terminate, terminated, termination
        [{"LEMMA": "cancel"}],                                     # cancel, cancelled, cancellation
        [{"LOWER": "expiry"}],
        [{"LOWER": "end"}, {"LOWER": "of"}, {"LOWER": "agreement"}],
    ],

    "liability": [
        [{"LOWER": "liability"}],
        [{"LOWER": "liable"}],
        [{"LOWER": "damages"}],
        [{"LEMMA": "indemnify"}],                                  # indemnify, indemnified, indemnification
        [{"LOWER": "hold"}, {"LOWER": "harmless"}],                # 2-word phrase
        [{"LOWER": "limitation"}, {"LOWER": "of"}, {"LOWER": "liability"}],
    ],

    "governing_law": [
        [{"LOWER": "governing"}, {"LOWER": "law"}],
        [{"LOWER": "jurisdiction"}],
        [{"LOWER": "venue"}],
        [{"LOWER": "governed"}, {"LOWER": "by"}],
    ],

    "force_majeure": [
        [{"LOWER": "force"}, {"LOWER": "majeure"}],
        [{"LOWER": "act"}, {"LOWER": "of"}, {"LOWER": "god"}],
        [{"LOWER": "unforeseeable"}],
    ],

    "intellectual_property": [
        [{"LOWER": "intellectual"}, {"LOWER": "property"}],        # full phrase — safe, no false positives
        [{"LOWER": "copyright"}],
        [{"LEMMA": "patent"}],
        [{"LOWER": "trademark"}],
    ],

    "dispute_resolution": [
        [{"LOWER": "arbitration"}],
        [{"LOWER": "mediation"}],
        [{"LOWER": "dispute"}, {"LOWER": "resolution"}],
        [{"LEMMA": "resolve"}],
    ],

    "assignment": [
    [{"LOWER": "assignment"}],        # only the noun form
    [{"LOWER": "assign"}, {"LOWER": "to"}],  # "assign to" — more specific
    [{"LEMMA": "transfer"}, {"LOWER": "of"}],
],

    "notice": [
        [{"LOWER": "notice"}],
        [{"LEMMA": "notify"}],                                     # notify, notified, notification
        [{"LOWER": "notification"}],
    ],
}


# ---------------------------------------------------------------------------
# STEP 3: Build the Matcher once at module level
# ---------------------------------------------------------------------------
# matcher.add(label, patterns):
#   label    = clause type string, returned when a match is found
#   patterns = list of pattern lists (OR logic between them)
# ---------------------------------------------------------------------------
def _build_matcher(nlp):
    matcher = Matcher(nlp.vocab)
    for clause_type, patterns in CLAUSE_PATTERNS.items():
        matcher.add(clause_type, patterns)
    return matcher

_matcher = _build_matcher(nlp)


# ---------------------------------------------------------------------------
# FUNCTION 1: classify_clause
# ---------------------------------------------------------------------------
# Input : raw clause text (string)
# Output: clause type label (string) e.g. "liability" or "unknown"
# ---------------------------------------------------------------------------
def classify_clause(clause_text: str) -> str:
    doc = nlp(clause_text)
    matches = _matcher(doc)
    if not matches:
        return "unknown"
    match_id, start, end = matches[0]
    return nlp.vocab.strings[match_id]


# ---------------------------------------------------------------------------
# FUNCTION 2: classify_clause_with_evidence
# ---------------------------------------------------------------------------
# Same as above but also returns the matched text — useful for debugging
# and for showing evidence in the UI ("matched on: indemnification")
# ---------------------------------------------------------------------------
def classify_clause_with_evidence(clause_text: str) -> dict:
    doc = nlp(clause_text)
    matches = _matcher(doc)

    if not matches:
        return {"type": "unknown", "matched_text": None}

    match_id, start, end = matches[0]
    clause_type = nlp.vocab.strings[match_id]

    # doc[start:end] is the Span — the actual tokens that triggered the match
    matched_text = doc[start:end].text

    return {
        "type": clause_type,
        "matched_text": matched_text
    }


# ---------------------------------------------------------------------------
# FUNCTION 3: extract_entities  ← NEW
# ---------------------------------------------------------------------------
# Input : raw clause text (string)
# Output: dict with four lists — persons, orgs, dates, locations
#
# How it works:
#   SpaCy's NER runs automatically when you call nlp(text).
#   doc.ents gives a list of Span objects, each with:
#     .text    → the actual text e.g. "Tata Consultancy Services"
#     .label_  → the category e.g. "ORG"
#
#   We filter by the four labels we care about:
#     PERSON → people's names
#     ORG    → companies, institutions
#     DATE   → dates, durations e.g. "1st January 2024", "30 days"
#     GPE    → countries, cities, states (Geo-Political Entity)
#
# This is NOT hardcoded by us — SpaCy's model learned this from training data.
# We just read the output and bucket it.
#
# Limitation: en_core_web_sm is a small general model.
# It may miss some Indian company names or legal-specific date formats.
# For production, en_core_web_trf (transformer-based) would be more accurate.
# ---------------------------------------------------------------------------
def extract_entities(clause_text: str) -> dict:
    doc = nlp(clause_text)

    entities = {
        "persons": [],
        "orgs": [],
        "dates": [],
        "locations": []
    }

    # Map SpaCy's label names to our bucket names
    label_map = {
        "PERSON": "persons",
        "ORG":    "orgs",
        "DATE":   "dates",
        "GPE":    "locations"
    }

    for ent in doc.ents:
        # ent.label_ is the SpaCy category string e.g. "ORG"
        # label_map.get() returns our bucket name, or None if we don't care about this label
        bucket = label_map.get(ent.label_)
        if bucket:
            # Avoid duplicates
            if ent.text not in entities[bucket]:
                entities[bucket].append(ent.text)

    return entities