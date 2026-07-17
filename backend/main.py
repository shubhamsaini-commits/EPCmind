from fastapi import FastAPI 
from fastapi import UploadFile , File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag import ask_with_rag 
from compilance import run_compliance_check
from vector_store import add_chunks
from vector_store import search
from vector_store import _collection
from vector_store import list_documents
from vector_store import get_stats
from chunker import chunk_document
from exctractors import extract_file
import os 
import shutil



app = FastAPI(title="EPC Intelligence API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}


class AskRequest(BaseModel):
    question : str
    document_type : str | None = None

@app.post("/ask")
def ask(req : AskRequest):
    chunks = search(req.question, filter_document_type = req.document_type)
    answer = ask_with_rag(req.question, filter_document_type = req.document_type)

    sources = [
        {
            "filename" : c["metadata"]["filename"],
            "document_type": c["metadata"]["document_type"],
            "text": c["text"],
            "distance": c["distance"],
        }
        for c in chunks
    ]
    return {"answer" : answer , "sources": sources}


@app.get("/documents")
def get_documents():
    return {"documents": list_documents()}


# upload mechanism
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploaded_docs")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload")
def upload_document(file: UploadFile = File(...)):
    save_path = os.path.join(UPLOAD_DIR, file.filename)

    # Save the uploaded file to disk first
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run it through your existing pipeline — identical to what ingest.py does
    try:
        extracted = extract_file(save_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    chunks = chunk_document(extracted)

    if not chunks:
        return {"status": "error", "message": "No content could be extracted from this file."}

    add_chunks(chunks)

    return {
        "filename": file.filename,
        "document_type": chunks[0]["document_type"],
        "chunks_added": len(chunks),
        "status": "success",
    }

last_compliance_results = []  # module-level, updated by /compliance-check

@app.post("/compliance-check")
def compliance_check():
    global last_compliance_results
    results = run_compliance_check()
    last_compliance_results = results
    return {"results": results}


@app.get("/stats")
def stats():
    data = get_stats()
    deviations = sum(1 for r in last_compliance_results if r.get("status") == "Deviation")
    return {
        "total_documents": data["total_documents"],
        "total_chunks": data["total_chunks"],
        "deviations_found": deviations,
    }
