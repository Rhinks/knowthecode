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


def repo_processor(repo_url: str, progress_callback=None) -> str:
    """Ingest a GitHub repository: clone, parse, chunk, and embed."""
    repo_id = repo_loader.get_repo_name_from_url(repo_url)
    
    if embedder.namespace_exists("code-chunks", repo_id):
        return repo_id
    
    try:
        repo_dir = repo_loader.ingest_repo(repo_url)
        repo_data = file_reader.read_repo_files(repo_dir)
        file_reader.save_files_to_json(repo_data, "output.json")
        
        chunks = chunker.chunk_and_save("output.json", "result.json")
        embedder.embed_chunks(chunks, index_name="code-chunks", repo_id=repo_id)
        
        return repo_id
    except Exception as e:
        print(f"Error processing repository: {e}")
        return None


def query_processor(query: str, repo_id: str, top_k: int = 5, progress_callback=None) -> str:
    """Retrieve relevant code chunks and generate an answer using LLM."""
    chunks = embedder.retrieve_chunks(query, index_name="code-chunks", repo_id=repo_id, top_k=top_k)
    
    if not chunks:
        return "No relevant information found in the repository."
    
    context = "\n\n---\n\n".join([
        f"File: {c['metadata'].get('file_path', 'N/A')}\n{c['metadata'].get('text', '')}" 
        for c in chunks
    ])
    
    system_prompt = "You are a code assistant. Answer questions based on provided code snippets. Be concise and include examples when relevant."
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return None


if __name__ == "__main__":
    query="what is this project about" #temporary
    repo_id = repo_processor("https://github.com/samarth-p/College-ERP.git")
    query_processor(query=query, repo_id=repo_id, top_k=5)