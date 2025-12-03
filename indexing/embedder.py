def embed_chunks(chunks: list[dict]):
    """
    Converts text chunks into embedding vectors using an embedding model (via LangChain/LlamaIndex).
    Does NOT store anything in a vector DB – just returns:
      - vectors: numeric embeddings (e.g., numpy array or list[list[float]])
      - metadata: list of metadata dicts aligned with vectors (chunk_id, file_path, repo_id, etc.)
    """


def store_embeddings(vectors, metadata, repo_id) -> None:
    """
    Store embeddings in a FAISS index and persist it to disk.
    - vectors: embedding matrix
    - metadata: list of dicts (chunk_id, file_path, repo_id, etc.)
    - repo_id: identifier for the repo (e.g., derived from repo URL)
    Also persists metadata (JSON/SQLite) so we can map FAISS IDs back to chunks.
    Called once per ingestion run after embeddings are generated.
    """
