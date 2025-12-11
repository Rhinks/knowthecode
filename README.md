# KnowTheCode

**AI-powered code repository analysis using RAG (Retrieval-Augmented Generation).**

Ask questions about any GitHub repository and get AI-generated answers based on the actual source code. Built with Python, FastAPI, OpenAI, and Pinecone.

## How It Works

1. **Ingest**: Clone a repository, parse files, and break code into semantic chunks using Tree-Sitter
2. **Embed**: Generate vector embeddings for code chunks using OpenAI's API
3. **Store**: Index embeddings in Pinecone for fast similarity search
4. **Query**: Retrieve relevant code chunks and generate answers using GPT-4o-mini

## Quick Start

### Prerequisites

- Python 3.8+
- [OpenAI API key](https://platform.openai.com)
- [Pinecone API key](https://www.pinecone.io)

### Setup

```bash
# Clone and enter directory
git clone <repo> && cd knowthecode

# Create virtual environment
python3 -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with API keys
echo "OPENAI_API_KEY=your_key_here" > .env
echo "PINECONE_API_KEY=your_key_here" >> .env
```

### Run

```bash
python3 api.py
```

Open `http://localhost:8000` in your browser.

## Features

- **Multi-language support**: Python, JavaScript, TypeScript, Java, Go, Rust, PHP, C/C++, HTML, CSS, and more
- **Intelligent chunking**: Uses Tree-Sitter for language-aware code segmentation
- **Vector search**: Fast semantic search via Pinecone
- **Smart caching**: Detects already-indexed repositories and skips re-processing
- **Clean UI**: Modern glass-morphism interface with real-time feedback

## Architecture

```
┌─────────────────┐
│  GitHub Repo    │
└────────┬────────┘
         │ git clone
         ▼
┌─────────────────┐
│ Parse & Chunk   │ Tree-Sitter
│ (orchestrator)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embed & Index   │ OpenAI + Pinecone
│ (embedder)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────┐
│   Pinecone      │◄─────┤   Query  │
│  Vector DB      │      └──────────┘
└─────────────────┘

Query Flow:
User Question → Embed → Search Pinecone → Retrieve Context → GPT-4o-mini → Answer
```

## Tech Stack

- **Backend**: FastAPI, Python 3
- **Parsing**: Tree-Sitter (code-aware chunking)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: Pinecone (serverless)
- **LLM**: GPT-4o-mini
- **Frontend**: Vanilla JS, CSS (glass-morphism design)

## Configuration

### Supported Languages

Code files: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.cpp`, `.c`, `.h`, `.go`, `.rs`, `.php`

Markup: `.html`, `.css`, `.scss`, `.json`, `.yaml`, `.xml`

Docs: `.md`, `.Rmd`, `.ipynb`

### Excluded Directories

Automatically skipped: `.git`, `node_modules`, `dist`, `build`, `venv`, `.env`, `__pycache__`, `.vscode`, etc.

## Future Enhancements

- [ ] Streaming ingestion progress (WebSocket)
- [ ] Support for private GitHub repositories (authentication)
- [ ] Custom chunking strategies per language
- [ ] Multi-turn conversation memory
- [ ] Code execution environment for validation
- [ ] Docker containerization for easy deployment
- [ ] Rate limiting and user authentication

## Notes

- First ingestion of a large repo may take 5-10 minutes
- Already-indexed repositories are automatically detected and cached
- Each repository gets its own Pinecone namespace
