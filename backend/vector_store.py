import chromadb
from llm_api_provider import embed_text
import os
import uuid
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

os.makedirs(CHROMA_PATH, exist_ok=True)
_chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _chroma_client.get_or_create_collection(name="epc_documents")


def _build_where(session_id: str, filter_document_type: str = None):
    conditions = [{"session_id": {"$eq": session_id}}]
    if filter_document_type:
        conditions.append({"document_type": {"$eq": filter_document_type}})

    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def add_chunks(chunks: list[dict], session_id: str):
    print(f"ADD_CHUNKS called with session_id:{session_id}")
    ids = []
    texts = []
    metadatas = []
    embeddings = []

    for chunk in chunks:
        ids.append(f"{session_id}_{chunk['chunk_id']}_{uuid.uuid4().hex[:8]}")   # STEP: unique ID
        texts.append(chunk["text"])
        embeddings.append(embed_text(chunk["text"]))
        metadatas.append({
            "filename": chunk["filename"],
            "filetype": chunk["filetype"],
            "doc_type": chunk["doc_type"],
            "document_type": chunk["document_type"],
            "session_id": session_id,
        })

    print(f"ADD_CHUNKS metadata sample: {metadatas[0] if metadatas else 'NONE'}")

    _collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search(query: str, session_id: str, n_results: int = 5, filter_document_type: str = None):
    query_embedding = embed_text(query)

    where_filter = _build_where(session_id, filter_document_type)

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
    )

    matches = []
    for i in range(len(results["ids"][0])):
        matches.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return matches


def list_documents(session_id: str):
    print(f"LIST_DOCUMENTS called with session_id:{session_id}")

    all_raw = _collection.get(include=["metadatas"])
    print(f"TOTAL chunks in collection (no filter): {len(all_raw['metadatas'])}")
    if all_raw["metadatas"]:
        print(f"Sample metadata from collection: {all_raw['metadatas'][0]}")

    all_data = _collection.get(
        where={"session_id": {"$eq": session_id}},
        include=["metadatas"]
    )
    print(f"FILTERED chunks matching session_id: {len(all_data['metadatas'])}")

    grouped = {}
    for metadata in all_data["metadatas"]:
        filename = metadata["filename"]
        if filename not in grouped:
            grouped[filename] = {
                "filename": filename,
                "document_type": metadata["document_type"],
                "filetype": metadata["filetype"],
                "chunk_count": 0,
            }
        grouped[filename]["chunk_count"] += 1

    return list(grouped.values())


def get_stats(session_id: str):
    documents = list_documents(session_id=session_id)
    total_documents = len(documents)
    total_chunks = sum(doc["chunk_count"] for doc in documents)

    return {
        "total_documents": total_documents,
        "total_chunks": total_chunks,
    }


def delete_document(filename: str, session_id: str):
    _collection.delete(
        where={
            "$and": [
                {"filename": {"$eq": filename}},
                {"session_id": {"$eq": session_id}},
            ]
        }
    )