from vector_store import search
from llm_api_provider import ask_ai

def ask_with_rag(question: str, session_id: str, n_results: int = 5, filter_document_type: str = None):
    """
    STEP: `session_id` naya required parameter add kiya function signature mein,
    aur `search()` call mein pass kiya.
    WHY: `main.py` ke `/ask` endpoint se ab `session_id` yahan tak aayega,
    taaki RAG sirf usi user ke documents se context banaye — doosre users ke
    documents is answer mein kabhi include nahi honge.
    """
    chunks = search(question, session_id=session_id, n_results=n_results, filter_document_type=filter_document_type)

    if not chunks:
        return "No relevant information found in the documents."

    context_blocks = []
    for i, c in enumerate(chunks):
        context_blocks.append(
            f"[Source {i+1}: {c['metadata']['document_type']} — {c['metadata']['filename']}]\n{c['text']}"
        )
    context = "\n\n".join(context_blocks)

    prompt = f"""You are an AI assistant for a data centre EPC project. Answer the question using ONLY the context below. If the answer isn't in the context, say so clearly. Cite which source(s) you used by number.

CONTEXT:
{context}

QUESTION: {question}

ANSWER (cite sources like [Source 1], [Source 2]):"""

    return ask_ai(prompt)


if __name__ == "__main__":
    # STEP: test block mein bhi session_id dena zaroori hai ab.
    # WHY: bina isके ye standalone test crash karega, kyunki function ab
    # session_id ke bina call hi nahi ho sakta.
    question = "What is the battery backup requirement, and does the vendor submittal match it?"
    answer = ask_with_rag(question, session_id="test-session")
    print(answer)