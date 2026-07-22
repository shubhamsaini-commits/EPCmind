from fastapi.responses import FileResponse
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
from owner_store import register_workspace, is_owner


app = FastAPI(title="EPC Intelligence API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_COOKIE_NAME = "session_id"


from fastapi import HTTPException

def get_session_id(request: Request, response: Response = None) -> str:
    """
    STEP: Poora function logic badla — cookie padhne ki jagah ab
    'X-Workspace-Id' header padhta hai.
    WHY: Workspace code ab user khud decide karta hai (Create/Join se),
    isliye backend ko naya ID generate karne ki zaroorat nahi — sirf
    jo bhi ID frontend bheje, wahi use karo. Agar header missing hai,
    matlab user ne abhi tak koi workspace choose nahi kiya — clear
    error do taaki frontend use "select a workspace" screen dikha sake.
    """
    workspace_id = request.headers.get("X-Workspace-Id")
    if not workspace_id:
        raise HTTPException(
            status_code=400,
            detail="No workspace selected. Please create or join a workspace first."
        )
    return workspace_id

@app.post("/workspace/create")
def create_workspace(request: Request):
    """
    STEP: Naya endpoint.
    WHY: Jab frontend pe user 'Create Workspace' dabaye, ye endpoint
    call hoga — request mein jo naya workspace_id (X-Workspace-Id header
    mein) frontend ne generate kiya hai, use yaha register karke ek
    secret owner_key banayenge aur wapas bhejenge. Ye key sirf creator
    ke paas jayegi.
    """
    workspace_id = get_session_id(request, None)
    owner_key = register_workspace(workspace_id)
    return {"workspace_id": workspace_id, "owner_key": owner_key}

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

    # STEP: Naya check add kiya — owner_key header verify karna.
    # WHY: Sirf workspace ka creator hi delete kar sake, koi bhi
    # joined member nahi. Header missing ya galat hone par 403 error.
    owner_key = request.headers.get("X-Owner-Key")
    if not is_owner(session_id, owner_key):
        raise HTTPException(
            status_code=403,
            detail="Only the workspace creator can delete documents."
        )

    delete_document(filename, session_id=session_id)

    file_path = os.path.join(UPLOAD_DIR, session_id, filename)   # STEP: workspace folder ke andar dhoondo
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"status": "success", "message": f"{filename} removed"}

#New endpoint
@app.get("/documents/{filename}/file")
def get_document_file(filename: str, request: Request, response: Response):
    """
    STEP: Naya endpoint — file ko actual serve karta hai.
    WHY: Frontend mein filename pe click karte hi ye endpoint call hoga,
    jo sirf usi workspace ke folder se file dhoondh ke bhejega —
    doosre workspace ki same-naam file kabhi accidentally nahi khulegi.
    """
    session_id = get_session_id(request, response)
    safe_filename = os.path.basename(filename)  # extra safety, path traversal se bachne ke liye
    file_path = os.path.join(UPLOAD_DIR, session_id, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in your workspace.")

    return FileResponse(file_path, filename=safe_filename)

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

    # STEP: Workspace-specific subfolder banaya.
    # WHY: Har workspace ki files apne alag folder mein rahein, taaki
    # do alag workspaces mein same filename ho to bhi collision na ho.
    workspace_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(workspace_dir, exist_ok=True)

    save_path = os.path.join(workspace_dir, safe_filename)

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