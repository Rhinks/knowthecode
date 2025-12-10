import sys
print("[DEBUG] Starting embedder.py import...")

try:
    from openai import OpenAI
    print("[DEBUG] ✓ openai imported")
except Exception as e:
    print(f"[ERROR] Failed to import openai: {e}")
    sys.exit(1)

try:
    from pinecone import Pinecone
    print("[DEBUG] ✓ pinecone imported")
except Exception as e:
    print(f"[ERROR] Failed to import pinecone: {e}")
    sys.exit(1)

from dotenv import load_dotenv
import os
import json

print("[DEBUG] Loading environment variables...")
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

print(f"[DEBUG] OPENAI_API_KEY: {'SET' if OPENAI_API_KEY else 'NOT SET'}")
print(f"[DEBUG] PINECONE_API_KEY: {'SET' if PINECONE_API_KEY else 'NOT SET'}")

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    print("[ERROR] Missing API keys in .env file")
    sys.exit(1)

print("[DEBUG] Initializing OpenAI client...")
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("[DEBUG] ✓ OpenAI client initialized")
except Exception as e:
    print(f"[ERROR] Failed to initialize OpenAI client: {e}")
    sys.exit(1)

print("[DEBUG] Initializing Pinecone client...")
try:
    pc = Pinecone(api_key=PINECONE_API_KEY)
    print("[DEBUG] ✓ Pinecone client initialized")
except Exception as e:
    print(f"[ERROR] Failed to initialize Pinecone client: {e}")
    sys.exit(1)

print("[DEBUG] ✓ embedder.py fully initialized\n")


def namespace_exists(index_name: str, repo_id: str) -> bool:
    """
    Check if a namespace (repo_id) already exists in the index.
    
    Args:
        index_name: Pinecone index name
        repo_id: namespace to check
    
    Returns:
        True if namespace exists, False otherwise
    """
    try:
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        namespaces = stats.get('namespaces', {})
        return repo_id in namespaces
    except Exception as e:
        print(f"[ERROR] Failed to check namespace: {e}")
        return False

def embed_chunks(chunks: list[dict], index_name: str = "code-chunks", repo_id: str = "default"):
    """
    Embed chunks using OpenAI and store in Pinecone.
    
    Args:
        chunks: list of dicts with keys: path, content, lang, start_line, end_line, id
        index_name: Pinecone index name (creates if doesn't `exist`)
        repo_id: identifier for the repo (for filtering)
    
    Returns:
        dict with stats: {num_embedded, total_tokens, index_name}
    """
    print(f"[embed_chunks] Starting with {len(chunks)} chunks")
    
    if not chunks:
        print("[ERROR] No chunks provided")
        return None
    
    # Filter out chunks with empty text
    print("[embed_chunks] Filtering out chunks with empty text...")
    valid_chunks = [c for c in chunks if c.get("text", "").strip()]
    print(f"[embed_chunks] Valid chunks: {len(valid_chunks)} (filtered {len(chunks) - len(valid_chunks)})")
    
    if not valid_chunks:
        print("[ERROR] No valid chunks after filtering")
        return None
    
    # Extract text from valid chunks
    print("[embed_chunks] Extracting text from chunks...")
    texts = [chunk.get("text", "").strip() for chunk in valid_chunks]
    print(f"[embed_chunks] Extracted {len(texts)} texts")
    
    # Call OpenAI API
    print("[embed_chunks] Calling OpenAI embedding API...")
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        embeddings = [item.embedding for item in response.data]
        total_tokens = response.usage.total_tokens
        print("[embed_chunks] ✓ API call successful")
    except Exception as e:
        print(f"[ERROR] OpenAI API call failed: {e}")
        return None
    
    print(f"[embed_chunks] Total tokens used: {total_tokens}")
    print(f"[embed_chunks] Embeddings shape: {len(embeddings)} x {len(embeddings[0]) if embeddings else 0}")
    
    # Get or create Pinecone index
    print(f"[embed_chunks] Checking Pinecone index '{index_name}'...")
    try:
        index = pc.Index(index_name)
        print(f"[embed_chunks] ✓ Using existing index: {index_name}")
    except Exception as e:
        print(f"[embed_chunks] Index not found, creating new index: {index_name}")
        try:
            pc.create_index(
                name=index_name,
                dimension=1536,  # OpenAI text-embedding-3-small dimension
                metric="cosine",
                spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
            )
            print(f"[embed_chunks] ✓ Index created: {index_name}")
            index = pc.Index(index_name)
        except Exception as create_error:
            print(f"[ERROR] Failed to create index: {create_error}")
            return None
    
    # Prepare vectors for Pinecone (ID, embedding, metadata)
    print("[embed_chunks] Preparing vectors for Pinecone...")
    vectors_to_upsert = []
    for i, chunk in enumerate(valid_chunks):
        vector_id = chunk.get("id", f"chunk_{i}")
        metadata = {
            "file_path": chunk.get("path", ""),
            "text": chunk.get("text", "")[:500],  # First 500 chars for context
            "lang": chunk.get("lang", "unknown"),
            "start_line": chunk.get("start_line", 0),
            "end_line": chunk.get("end_line", 0),
            "repo_id": repo_id,
        }
        vectors_to_upsert.append((vector_id, embeddings[i], metadata))
    
    print(f"[embed_chunks] Prepared {len(vectors_to_upsert)} vectors")
    
    # Upsert to Pinecone
    print(f"[embed_chunks] Upserting vectors to Pinecone (namespace: {repo_id})...")
    try:
        index.upsert(vectors=vectors_to_upsert, namespace=repo_id)
        print(f"[embed_chunks] ✓ Upsert successful")
    except Exception as e:
        print(f"[ERROR] Upsert failed: {e}")
        return None
    
    print(f"[embed_chunks] ✓ Successfully embedded and stored {len(chunks)} chunks")
    return {
        "num_embedded": len(chunks),
        "total_tokens": total_tokens,
        "index_name": index_name,
        "repo_id": repo_id
    }

def retrieve_chunks(query: str, index_name: str = "code-chunks", repo_id: str = "default", top_k: int = 5):
    """
    Retrieve relevant chunks from Pinecone based on a query.
    
    Args:
        query: user's natural language question
        index_name: Pinecone index name
        repo_id: repo identifier (filters by namespace)
        top_k: number of results to return
    
    Returns:
        list of dicts with chunk metadata and similarity score
    """
    print(f"[retrieve_chunks] Embedding query: '{query}'")
    
    try:
        # Embed the query
        query_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        )
        query_embedding = query_response.data[0].embedding
        print("[retrieve_chunks] ✓ Query embedded")
    except Exception as e:
        print(f"[ERROR] Failed to embed query: {e}")
        return []
    
    # Search Pinecone
    print(f"[retrieve_chunks] Searching Pinecone (top_k={top_k})...")
    try:
        index = pc.Index(index_name)
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=repo_id,
            include_metadata=True
        )
        print(f"[retrieve_chunks] ✓ Found {len(results.get('matches', []))} results")
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        return []
    
    # Format results
    retrieved = []
    for match in results.get("matches", []):
        retrieved.append({
            "id": match["id"],
            "score": match["score"],
            "metadata": match.get("metadata", {})
        })
    
    return retrieved


def namespace_exists(index_name: str, repo_id: str) -> bool:
    """
    Check if a namespace (repo_id) already exists in the Pinecone index.
    
    Args:
        index_name: Pinecone index name
        repo_id: namespace to check
    
    Returns:
        True if namespace exists, False otherwise
    """
    try:
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        namespaces = stats.get('namespaces', {})
        exists = repo_id in namespaces
        print(f"[namespace_exists] Checking '{repo_id}' in index '{index_name}': {exists}")
        return exists
    except Exception as e:
        print(f"[ERROR] Failed to check namespace: {e}")
        return False


# ============================================================
# TEST CODE (run this file directly to test)
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("STARTING TEST: Embedding and Retrieval")
    print("="*60 + "\n")
    
    # Step 1: Load chunks
    print("[STEP 1] Loading result.json...")
    try:
        with open("result.json") as f:
            chunks = json.load(f)
        print(f"✓ Loaded {len(chunks)} chunks\n")
    except Exception as e:
        print(f"✗ Error loading result.json: {e}")
        sys.exit(1)
    
    # Step 2: Embed chunks
    print("[STEP 2] Embedding chunks with OpenAI...")
    stats = embed_chunks(chunks, index_name="code-chunks", repo_id="flask")
    if stats:
        print(f"\n✓ Embedding successful!")
        print(f"  - Chunks: {stats['num_embedded']}")
        print(f"  - Tokens: {stats['total_tokens']}")
        print(f"  - Index: {stats['index_name']}")
        print(f"  - Repo: {stats['repo_id']}\n")
    else:
        print("✗ Embedding failed")
        sys.exit(1)
    
    # Step 3: Test retrieval
    print("[STEP 3] Testing retrieval with sample queries...")
    test_queries = [
        "How do I handle HTTP requests?",
        "What is the Flask app structure?",
        "How do I create routes?",
    ]
    
    for query in test_queries:
        print(f"\n  Query: '{query}'")
        results = retrieve_chunks(query, index_name="code-chunks", repo_id="flask", top_k=2)
        
        if results:
            for idx, result in enumerate(results, 1):
                meta = result['metadata']
                score = result['score']
                print(f"    [{idx}] Score: {score:.3f} | File: {meta.get('file_path', 'N/A')} | Lang: {meta.get('lang', 'N/A')}")
                print(f"        Text: {meta.get('text', 'N/A')[:100]}...")
        else:
            print("    No results found")
    
    print("\n" + "="*60)
    print("✓ TEST COMPLETE")
    print("="*60)
