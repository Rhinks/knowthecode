import sys
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
import os
import json

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    print("Error: Missing API keys in .env file")
    sys.exit(1)

openai_client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)


def namespace_exists(index_name: str, repo_id: str) -> bool:
    """Check if a namespace exists in Pinecone."""
    try:
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        return repo_id in stats.get('namespaces', {})
    except Exception:
        return False

def embed_chunks(chunks: list[dict], index_name: str = "code-chunks", repo_id: str = "default"):
    """Embed code chunks and store in Pinecone vector database."""
    if not chunks:
        return None
    
    valid_chunks = [c for c in chunks if c.get("text", "").strip()]
    if not valid_chunks:
        return None
    
    texts = [chunk.get("text", "").strip() for chunk in valid_chunks]
    
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        embeddings = [item.embedding for item in response.data]
        total_tokens = response.usage.total_tokens
    except Exception as e:
        print(f"Error embedding chunks: {e}")
        return None
    
    try:
        index = pc.Index(index_name)
    except:
        try:
            pc.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
            )
            index = pc.Index(index_name)
        except Exception as e:
            print(f"Error creating index: {e}")
            return None
    
    vectors = []
    for i, chunk in enumerate(valid_chunks):
        vectors.append((
            chunk.get("id", f"chunk_{i}"),
            embeddings[i],
            {
                "file_path": chunk.get("path", ""),
                "text": chunk.get("text", "")[:500],
                "lang": chunk.get("lang", "unknown"),
                "start_line": chunk.get("start_line", 0),
                "end_line": chunk.get("end_line", 0),
                "repo_id": repo_id,
            }
        ))
    
    batch_size = 25
    try:
        for i in range(0, len(vectors), batch_size):
            index.upsert(vectors=vectors[i:i + batch_size], namespace=repo_id)
    except Exception as e:
        print(f"Error upserting to Pinecone: {e}")
        return None
    
    return {
        "num_embedded": len(chunks),
        "total_tokens": total_tokens,
        "index_name": index_name,
        "repo_id": repo_id
    }

def retrieve_chunks(query: str, index_name: str = "code-chunks", repo_id: str = "default", top_k: int = 5):
    """Retrieve relevant code chunks from Pinecone based on query similarity."""
    try:
        query_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        )
        query_embedding = query_response.data[0].embedding
    except Exception as e:
        print(f"Error embedding query: {e}")
        return []
    
    try:
        index = pc.Index(index_name)
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=repo_id,
            include_metadata=True
        )
    except Exception as e:
        print(f"Error searching Pinecone: {e}")
        return []
    
    return [
        {
            "id": match["id"],
            "score": match["score"],
            "metadata": match.get("metadata", {})
        }
        for match in results.get("matches", [])
    ]


def namespace_exists(index_name: str, repo_id: str) -> bool:
    """
    Check if a namespace (repo_id) already exists in the Pinecone index.
    Uses a simple query to check if namespace has any vectors.
    
    Args:
        index_name: Pinecone index name
        repo_id: namespace to check
    
    Returns:
        True if namespace exists and has vectors, False otherwise
    """
    try:
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        namespaces = stats.get('namespaces', {})
        
        if repo_id in namespaces:
            print(f"[namespace_exists] ✓ Namespace '{repo_id}' found in stats")
            return True
        
        print(f"[namespace_exists] ✗ Namespace '{repo_id}' NOT found in stats")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to check namespace: {e}")
        print(f"[DEBUG] This might mean the namespace truly doesn't exist yet")
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
