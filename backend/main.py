from fastapi import FastAPI, Request, Response
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag import ask_with_rag
from compilance import run_compliance_check
from vector_store import add_chunks
from vector_store import search
from vector_store import _collection
from vector_store import list_documents, delete_document
from vector_store import get_stats
from chunker import chunk_document
from exctractors import extract_file
import os
import shutil
import uuid
from compilance import save_compliance_results, load_compliance_results


app = FastAPI(title="EPC Intelligence API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_COOKIE_NAME = "session_id"


def get_session_id(request: Request, response: Response) -> str:
    """
    Reads the session_id cookie if present, otherwise generates a new one
    and sets it on the response. This gives each browser/user its own
    isolated view of documents without requiring login.
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=60 * 60 * 24 * 30,  # 30 days
            httponly=True,
            samesite="lax",
        )
    return session_id


@app.get("/")
def root():
    return {"status": "ok"}


class AskRequest(BaseModel):
    question: str
    document_type: str | None = None


@app.post("/ask")
def ask(req: AskRequest, request: Request, response: Response):
    session_id = get_session_id(request, response)

    chunks = search(req.question, filter_document_type=req.document_type, session_id=session_id)
    answer = ask_with_rag(req.question, filter_document_type=req.document_type, session_id=session_id)

    sources = [
        {
            "filename": c["metadata"]["filename"],
            "document_type": c["metadata"]["document_type"],
            "text": c["text"],
            "distance": c["distance"],
        }
        for c in chunks
    ]
    return {"answer": answer, "sources": sources}


@app.get("/documents")
def get_documents(request: Request, response: Response):
    session_id = get_session_id(request, response)
    print(f"DOCUMENTS session_id:{session_id}")
    return {"documents": list_documents(session_id=session_id)}
    

@app.delete("/documents/{filename}")
def remove_document(filename: str, request: Request, response: Response):
    session_id = get_session_id(request, response)

    # Only removes chunks belonging to this session's own document
    delete_document(filename, session_id=session_id)

    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"status": "success", "message": f"{filename} removed"}


# upload mechanism
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR",
    os.path.join(BASE_DIR, "uploaded_docs")
)

os.makedirs(UPLOAD_DIR, exist_ok=True)


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt", ".md"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB limit


@app.post("/upload")
def upload_document(file: UploadFile = File(...), request: Request = None, response: Response = None):
    session_id = get_session_id(request, response)
    print(f"UPLOAD session_id:{session_id}")
    safe_filename = os.path.basename(file.filename)
    file_ext = os.path.splitext(safe_filename)[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        return {"status": "error", "message": f"File type '{file_ext}' not allowed."}

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        return {"status": "error", "message": "File too large. Max size is 20 MB"}

    save_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(save_path, "wb") as f:
        f.write(content)

    try:
        extracted = extract_file(save_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    chunks = chunk_document(extracted)

    if not chunks:
        return {"status": "error", "message": "No content could be extracted from this file."}

    add_chunks(chunks, session_id=session_id)

    return {
        "filename": file.filename,
        "document_type": chunks[0]["document_type"],
        "chunks_added": len(chunks),
        "status": "success",
    }


@app.post("/compliance-check")
def compliance_check(request: Request, response: Response):
    session_id = get_session_id(request, response)
    results = run_compliance_check(session_id=session_id)
    if isinstance(results, dict) and "error" in results:
        return results
    data = save_compliance_results(results, session_id=session_id)
    return data


@app.get("/compliance-check")
def get_last_compliance_check(request: Request, response: Response):
    session_id = get_session_id(request, response)
    return load_compliance_results(session_id=session_id)

@app.get("/stats")
def stats(request: Request, response: Response):
    session_id = get_session_id(request, response)
    doc_data = get_stats(session_id=session_id)
    compliance_data = load_compliance_results(session_id=session_id)
    deviations = sum(1 for r in compliance_data["results"] if r.get("status") == "Deviation")
    return {
        "total_documents": doc_data["total_documents"],
        "total_chunks": doc_data["total_chunks"],
        "deviations_found": deviations,
    }