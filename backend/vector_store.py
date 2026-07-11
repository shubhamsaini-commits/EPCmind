import chromadb
from llm_api_provider import embed_text

_chroma_client = chromadb.PersistentClient(path="./chroma_db")
_collection = _chroma_client.get_or_create_collection(name="epc_documents")


def add_chunks(chunks: list[dict]):
    """
    Embeds and stores a list of chunk dicts (from chunk_document())
    into ChromaDB.
    """
    ids = []
    texts = []
    metadatas = []
    embeddings = []

    for chunk in chunks:
        ids.append(chunk["chunk_id"])
        texts.append(chunk["text"])
        embeddings.append(embed_text(chunk["text"]))
        metadatas.append({
            "filename": chunk["filename"],
            "filetype": chunk["filetype"],
            "doc_type": chunk["doc_type"],
            "document_type": chunk["document_type"],
        })

    _collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search(query: str, n_results: int = 5, filter_document_type: str = None):
    """
    Embeds the query and finds the closest matching chunks.
    Optionally filter by document_type, e.g. "Vendor Submittal".
    """
    query_embedding = embed_text(query)

    where_filter = {"document_type": filter_document_type} if filter_document_type else None

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
            "distance": results["distances"][0][i],  # lower = more similar
        })
    return matches