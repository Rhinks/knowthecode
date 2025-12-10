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


def repo_processor(repo_url:str)->str:
    """    
    :param repo_url: repo_url entered by the user
    :type repo_url: str
    
    - clones the repo --> file_reading --> chunking --> embedder.py store in pinecone.
    - returns repo_id: to identify this repo later 
    
    """
    print("\n" + "="*60)
    print("[STEP 0] Extracting repo name and checking if already indexed...")
    print("="*60)
    
    # 0. Extract repo_id and check if already indexed
    repo_id = repo_loader.get_repo_name_from_url(repo_url)
    print(f"✓ Extracted repo_id: {repo_id}")
    
    if embedder.namespace_exists("code-chunks", repo_id):
        print(f"✓ Repo '{repo_id}' already indexed! Skipping processing.")
        return repo_id
    
    print(f"✓ Repo '{repo_id}' not found. Starting full pipeline...\n")
    
    # 1. clone the repo on my machine (for now, will later change to tmp for production) --> cloned_repos/repo_name
    print("="*60)
    print("[STEP 1] Cloning repository...")
    print("="*60)
    rep_dir = repo_loader.ingest_repo(repo_url) # will return repo_dir
    print(f"✓ Repository cloned to: {rep_dir}\n")

    # 2. run file_reader to filter out files to process --> output.json
    print("="*60)
    print("[STEP 2] Reading and parsing repository files...")
    print("="*60)
    repo_data = file_reader.read_repo_files(rep_dir) # will return list[dict]
    print(f"✓ Found {len(repo_data)} files to process")
    file_reader.save_files_to_json(repo_data, "output.json")
    print(f"✓ Saved to output.json\n")

    # 3. using chunker.py create chunking via tree-sitter --> result.json
    print("="*60)
    print("[STEP 3] Chunking files...")
    print("="*60)
    chunks = chunker.chunk_and_save("output.json", "result.json")  # create result.json
    print(f"✓ Created {len(chunks)} chunks\n")

    # 4. generate embbedding and indexing using embed_chunks.py (openai embeddings, pinecone for indexing) --> returns repo_id
    print("="*60)
    print("[STEP 4] Embedding chunks and indexing in Pinecone...")
    print("="*60)
    res_indexing = embedder.embed_chunks(chunks, index_name="code-chunks", repo_id=repo_id)
    
    if res_indexing:
        print(f"✓ Embedded {res_indexing['num_embedded']} chunks")
        print(f"✓ Used {res_indexing['total_tokens']} tokens")
        print(f"✓ Index: {res_indexing['index_name']}")
    else:
        print("✗ Embedding failed!")
        return None
    
    print("\n" + "="*60)
    print(f"✓ REPO PROCESSING COMPLETE for '{repo_id}'")
    print("="*60 + "\n")
    
    return repo_id


def query_processor(query:str, repo_id:str, top_k:int=5):
    """
    
    :param query: User's question
    :type query: str
    :param repo_id: repo_id to identify index in pinecone
    :type repo_id: str
    :param top_k: number of chunks to retrieve (default: 5)
    :type top_k: int

    user query + repo_id to search --> retrieve chunks --> feed chunks + query to llm --> return answer text

    called multiple times 

    """
    print("\n" + "="*60)
    print("[STEP 1] Retrieving relevant chunks from Pinecone...")
    print("="*60)
    print(f"Query: '{query}'")
    print(f"Repo ID: {repo_id}")
    print(f"Top K: {top_k}\n")

    chunks = embedder.retrieve_chunks(query, index_name="code-chunks", repo_id=repo_id, top_k=top_k)
    
    if not chunks:
        print("✗ No chunks retrieved!")
        return "I couldn't find relevant information in the repository."
    
    print(f"✓ Retrieved {len(chunks)} chunks\n")
    
    print("="*60)
    print("[STEP 2] Feeding chunks to LLM (GPT-4o-mini)...")
    print("="*60)
    
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
        print(f"✓ LLM response generated\n")
    except Exception as e:
        print(f"✗ LLM API call failed: {e}")
        return None

    print("="*60)
    print("ANSWER:")
    print("="*60)
    print(answer)
    print("="*60 + "\n")

    return answer

query="what is this project about" #temporary
repo_id = repo_processor("https://github.com/samarth-p/College-ERP.git")

query_processor(query=query, repo_id=repo_id, top_k=5)