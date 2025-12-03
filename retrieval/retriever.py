def retrieve(query: str, repo_id) -> list[dict]:
    """
    Retrieve the most relevant chunks for a query from the vector store.
    Steps:
      - Embed the query using the same embedding model.
      - Search FAISS for top-k similar vectors.
      - Filter results by repo_id using stored metadata.
      - Return a list of chunk dicts (text + metadata) for the LLM to use.
    This function does NOT call the LLM – it only returns context.
    """
