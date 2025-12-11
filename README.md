# KnowTheCode - AI-Powered Repository Analysis

An AI-powered code repository analysis tool that uses RAG (Retrieval-Augmented Generation) to answer questions about codebases.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Pinecone API key
- Git (for cloning repositories)

### Installation

1. **Clone or navigate to the project directory:**

   ```bash
   cd knowthecode
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   Create a `.env` file in the project root:

   ```bash
   touch .env
   ```

   Add your API keys:

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   PINECONE_API_KEY=your_pinecone_api_key_here
   ```

### Running the Application

1. **Start the FastAPI server:**

   ```bash
   python api.py
   ```

   Or using uvicorn directly:

   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```

   **Note:** When using `--reload`, exclude the cloned repos to avoid restart mid-ingestion:

   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload --reload-exclude ingestion/cloned_repos/**
   ```

2. **Open the frontend:**

   Open `index.html` in your web browser, or serve it with a simple HTTP server:

   ```bash
   # Python 3
   python -m http.server 8080

   # Then open: http://localhost:8080/index.html
   ```

   Or simply double-click `index.html` to open it in your default browser.

3. **Verify the API is running:**

   Visit: http://localhost:8000/health

   You should see: `{"status": "ok"}`

## 📖 Usage

1. **Ingest a Repository:**

   - Enter a GitHub repository URL (e.g., `https://github.com/user/repo.git`)
   - Click "Start Engine"
   - Watch live progress as the backend streams cloning/parsing/chunking/embedding updates

2. **Query the Repository:**
   - After ingestion, the query section will appear
   - Enter your question about the codebase
   - Adjust the "Top K" slider to control how many chunks to retrieve (1-10)
   - Click "Analyze & Generate"
   - View the AI-generated answer

## 🔧 Configuration

### Pinecone Index

The application uses a Pinecone index named `code-chunks`. If it doesn't exist, it will be automatically created with:

- Dimension: 1536 (for OpenAI text-embedding-3-small)
- Metric: cosine
- Cloud: AWS (us-east-1)

### Supported File Types

- Code: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.cpp`, `.c`, `.h`, `.go`, `.rs`, `.php`
- Web: `.html`, `.css`, `.scss`
- Data: `.json`, `.yaml`, `.yml`, `.xml`
- Docs: `.md`, `.Rmd`, `.ipynb`

### Ignored Directories

The following directories are automatically skipped:

- `.git`, `node_modules`, `dist`, `build`, `venv`, `env`, `__pycache__`, `.next`, `.vscode`, `vendor`, `.idea`

## 🧪 Testing

### Test the Chunker:

```bash
python scripts/check.py
```

### Test Embedding (requires result.json):

```bash
python indexing/embedder.py
```

### Test Full Pipeline:

```bash
python orchestrator.py
```

## 📁 Project Structure

```
knowthecode/
├── api.py              # FastAPI REST API server
├── orchestrator.py     # Main orchestration logic
├── index.html          # Frontend UI
├── requirements.txt    # Python dependencies
├── ingestion/          # Repository cloning
├── parsing/            # File reading & filtering
├── chunking/           # Code chunking (Tree-Sitter)
└── indexing/           # Embedding & Pinecone operations
```

## 🐛 Troubleshooting

### API Connection Errors

- Ensure the FastAPI server is running on port 8000
- Check that `index.html` has the correct API URL (`http://localhost:8000`)

### Missing API Keys

- Verify your `.env` file exists and contains both `OPENAI_API_KEY` and `PINECONE_API_KEY`
- Restart the server after adding/changing `.env` values

### Tree-Sitter Parsing Issues

- If Tree-Sitter parsers fail to load, the system will fall back to generic chunking
- Install Tree-Sitter language packages: `pip install tree-sitter-python tree-sitter-javascript` etc.

### Pinecone Index Errors

- Ensure your Pinecone API key has permission to create indexes
- Check your Pinecone account limits

## 📝 Notes

- The first ingestion of a repository may take several minutes depending on repository size
- Already indexed repositories are detected and skipped automatically
- Each repository is stored in a separate Pinecone namespace (using `repo_id`)
