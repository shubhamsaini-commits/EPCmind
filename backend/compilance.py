import json
import os
from datetime import datetime
from exctractors import extract_file
from llm_api_provider import ask_ai
from vector_store import list_documents

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_docs")
COMPLIANCE_FILE = os.path.join(BASE_DIR, "last_compliance_check.json")


def find_latest_document(doc_type_label, session_id):
    """
    STEP: Poora function logic badla — ab `os.listdir(UPLOAD_DIR)` se saari
    disk files scan karne ke bajaye, `vector_store.list_documents(session_id)`
    use kar rahe hain.
    WHY: Disk scan karne se HAR user ki files mil jaati thi (koi session
    knowledge disk pe nahi hoti). ChromaDB mein ab session_id metadata hai,
    isliye list_documents() sirf apne session ke documents deta hai —
    isi se compliance check bhi sirf apne documents tak limited rehta hai.
    """
    docs = list_documents(session_id=session_id)

    matches = []
    for doc in docs:
        if doc["document_type"] == doc_type_label:
            full_path = os.path.join(UPLOAD_DIR, session_id, doc["filename"])   # STEP: workspace folder bhi path mein include kiya
            if os.path.exists(full_path):
                matches.append(full_path)

    if not matches:
        return None

    return max(matches, key=os.path.getmtime)


def run_compliance_check(session_id):
    """
    STEP: `session_id` naya required parameter add kiya, `find_latest_document()`
    ke dono calls mein pass kiya.
    WHY: `main.py` se ab session_id yahan tak aayega taaki compliance check
    bhi sirf apne session ke Specification + Submittal compare kare.
    """
    spec_path = find_latest_document("Specification", session_id)
    submittal_path = find_latest_document("Vendor Submittal", session_id)

    if not spec_path or not submittal_path:
        return {
            "error": "Please upload both a Specification and a Vendor Submittal document before running compliance check."
        }

    spec = extract_file(spec_path)
    submittal = extract_file(submittal_path)

    prompt = f"""SPECIFICATION:
{spec['text']}

VENDOR SUBMITTAL:
{submittal['text']}

Compare every relevant requirement (battery autonomy, capacity, efficiency, topology, warranty, etc.) in the specification against the vendor submittal.

Respond with ONLY a JSON array, no markdown formatting, no explanation, no code fences. Each item must have exactly these fields:
- "requirement": short name of what's being compared
- "specified_value": the value from the specification, or "Not stated" if absent
- "submitted_value": the value from the submittal, or "Not stated" if absent
- "status": exactly one of "Match", "Deviation", or "Cannot verify"
- "severity": "Critical", "Moderate", or "Low" if status is "Deviation", otherwise null

IMPORTANT: If either specified_value or submitted_value is "Not stated", status MUST be "Cannot verify" — never "Match". A match requires both values to be actually present and equivalent.
Example format:
[{{"requirement": "Battery Autonomy", "specified_value": "15 minutes", "submitted_value": "10 minutes", "status": "Deviation", "severity": "Critical"}}]
"""

    raw_response = ask_ai(prompt)

    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        results = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    return results


COMPLIANCE_DIR = os.path.join(BASE_DIR, "compliance_results")
os.makedirs(COMPLIANCE_DIR, exist_ok=True)


def _compliance_file_for_session(session_id):
    """
    STEP: Naya helper function.
    WHY: Ab ek hi shared JSON file ki jagah, har session ki apni alag
    result file hogi (session_id ke naam se), taaki results bhi isolated rahein.
    """
    return os.path.join(COMPLIANCE_DIR, f"{session_id}.json")


def save_compliance_results(results, session_id):
    """
    STEP: `session_id` naya required parameter add kiya, aur file path ab
    `_compliance_file_for_session()` se aata hai (fixed COMPLIANCE_FILE ki jagah).
    WHY: Har session ka result apni alag file mein save ho, sab users ka
    result mix na ho ek hi file mein.
    """
    data = {
        "results": results,
        "ran_at": datetime.now().isoformat(),
    }
    file_path = _compliance_file_for_session(session_id)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def load_compliance_results(session_id):
    """
    STEP: `session_id` naya required parameter add kiya.
    WHY: Sirf usi session ki result file padhi jaye, doosre session ka
    result kabhi return na ho.
    """
    file_path = _compliance_file_for_session(session_id)
    if not os.path.exists(file_path):
        return {"results": [], "ran_at": None}
    with open(file_path, "r") as f:
        return json.load(f)