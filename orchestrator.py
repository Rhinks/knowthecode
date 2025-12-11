from ingestion import repo_loader
from parsing import file_reader
from chunking import chunker
from indexing import embedder
from git import Repo
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def repo_processor(repo_url:str, progress_callback=None)->str:
    """    
    :param repo_url: repo_url entered by the user
    :type repo_url: str
    
    - clones the repo --> file_reading --> chunking --> embedder.py store in pinecone.
    - returns repo_id: to identify this repo later 
    
    """
    def emit(msg):
        """Helper to send progress message"""
        if progress_callback:
            progress_callback(msg)
        print(msg)
    
    emit("\n[STEP 0] Extracting repo name and checking if already indexed...")
    
    # 0. Extract repo_id and check if already indexed
    repo_id = repo_loader.get_repo_name_from_url(repo_url)
    emit(f"✓ Extracted repo_id: {repo_id}")
    
    if embedder.namespace_exists("code-chunks", repo_id):
        emit(f"✓ Repo '{repo_id}' already indexed! Ready for queries.")
        return repo_id
    
    emit(f"✓ Repo not indexed. Starting full pipeline...\n")
    
    # 1. Clone
    emit("[STEP 1] Cloning repository...")
    try:
        rep_dir = repo_loader.ingest_repo(repo_url)
        emit(f"✓ Repository cloned\n")
    except Exception as e:
        emit(f"✗ Clone failed: {e}")
        return None

    # 2. Parse
    emit("[STEP 2] Reading and parsing repository files...")
    try:
        repo_data = file_reader.read_repo_files(rep_dir)
        emit(f"✓ Found {len(repo_data)} files")
        emit(f"Saving files to output.json...")
        file_reader.save_files_to_json(repo_data, "output.json")
        emit(f"✓ Files saved\n")
    except Exception as e:
        emit(f"✗ Parse failed: {e}")
        return None

    # 3. Chunk
    emit("[STEP 3] Chunking files with Tree-Sitter...")
    try:
        chunks = chunker.chunk_and_save("output.json", "result.json")
        emit(f"✓ Created {len(chunks)} chunks\n")
    except Exception as e:
        emit(f"✗ Chunking failed: {e}")
        return None

    # 4. Embed
    emit("[STEP 4] Embedding chunks with OpenAI...")
    try:
        res_indexing = embedder.embed_chunks(chunks, index_name="code-chunks", repo_id=repo_id)
    except Exception as e:
        emit(f"✗ Embedding failed: {e}")
        return None
    
    if res_indexing:
        emit(f"✓ Embedded {res_indexing['num_embedded']} chunks")
        emit(f"✓ Used {res_indexing['total_tokens']} tokens\n")
    else:
        emit("✗ Embedding failed!")
        return None
    
    emit(f"✓ COMPLETE - Repo '{repo_id}' ready for queries")
    
    return repo_id


def query_processor(query:str, repo_id:str, top_k:int=5, progress_callback=None):
    """
    
    :param query: User's question
    :type query: str
    :param repo_id: repo_id to identify index in pinecone
    :type repo_id: str
    :param top_k: number of chunks to retrieve (default: 5)
    :type top_k: int
    :param progress_callback: optional callback to report progress
    :type progress_callback: callable

    user query + repo_id to search --> retrieve chunks --> feed chunks + query to llm --> return answer text

    called multiple times 

    """
    def emit(msg):
        """Helper to send progress message"""
        if progress_callback:
            progress_callback(msg)
        print(msg)
    
    emit("\n[STEP 1] Retrieving relevant chunks from Pinecone...")

    chunks = embedder.retrieve_chunks(query, index_name="code-chunks", repo_id=repo_id, top_k=top_k)
    
    if not chunks:
        emit("✗ No chunks retrieved!")
        return "I couldn't find relevant information in the repository."
    
    emit(f"✓ Retrieved {len(chunks)} chunks\n")
    
    emit("[STEP 2] Feeding chunks to LLM (GPT-4o-mini)...")
    
    # Format chunks for LLM
    context = "\n\n---\n\n".join([
        f"File: {c['metadata'].get('file_path', 'N/A')}\nContent:\n{c['metadata'].get('text', 'N/A')}" 
        for c in chunks
    ])
    
    system_prompt = """You are a helpful code assistant. Answer the user's question based on the provided code snippets.
    Be concise and provide code examples when relevant. If you can't answer from the context, say so."""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ]
        )
        answer = response.choices[0].message.content
        emit(f"✓ LLM response generated\n")
    except Exception as e:
        emit(f"✗ LLM API call failed: {e}")
        return None

    emit("✓ COMPLETE - Answer ready")

    return answer


if __name__ == "__main__":
    query="what is this project about" #temporary
    repo_id = repo_processor("https://github.com/samarth-p/College-ERP.git")
    query_processor(query=query, repo_id=repo_id, top_k=5)