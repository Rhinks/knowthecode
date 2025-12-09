# Ingestion pipeline (called when user clicks "Ingest"):
#   1. ingest_repo(repo_url) -> repo_path
#   2. read_repo_files(repo_path) -> files
#   3. chunk_files(files) -> chunks
#   4. embed_chunks(chunks) -> vectors, metadata
#   5. store_embeddings(vectors, metadata, repo_id)

# Query pipeline (called when user asks a question):
#   1. retrieve(query, repo_id) -> chunks
#   2. call LLM (Gemini) with query + chunks
#   3. return answer to frontend



#call the repo loader -> file reader -> chunker -> embbedder -> retriever

