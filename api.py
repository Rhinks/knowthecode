import asyncio
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from orchestrator import repo_processor, query_processor

app = FastAPI(title="KnowTheCode API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Request/Response Models ==========
class IngestRequest(BaseModel):
    repo_url: str

class IngestResponse(BaseModel):
    repo_id: str
    status: str

class QueryRequest(BaseModel):
    repo_id: str
    query: str
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    repo_id: str
    query: str


# ========== Endpoints ==========

@app.post("/ingest", response_model=IngestResponse)
async def ingest_repository(request: IngestRequest):
    """Ingest a GitHub repository."""
    try:
        print(f"\n[API] /ingest endpoint called with: {request.repo_url}")
        
        # Run blocking code in a thread to avoid blocking the event loop
        repo_id = await asyncio.to_thread(repo_processor, request.repo_url)
        
        if repo_id is None:
            raise HTTPException(status_code=500, detail="Repository processing failed")
        
        return IngestResponse(repo_id=repo_id, status="success")
    
    except Exception as e:
        print(f"[API ERROR] /ingest failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_repository(request: QueryRequest):
    """Query a repository."""
    try:
        print(f"\n[API] /query endpoint called")
        
        answer = await asyncio.to_thread(query_processor, request.query, request.repo_id, request.top_k)
        
        if answer is None:
            raise HTTPException(status_code=500, detail="Query processing failed")
        
        return QueryResponse(answer=answer, repo_id=request.repo_id, query=request.query)
    
    except Exception as e:
        print(f"[API ERROR] /query failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# Serve static files (index.html)
@app.get("/")
async def root():
    """Serve index.html at root"""
    from fastapi.responses import FileResponse
    index_path = Path(__file__).parent / "index.html"
    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn
    print("Starting KnowTheCode API...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )