import os
import json
from pathlib import Path
from typing import List, Dict


IGNORED_DIRS = {'.git', 'node_modules', 'dist', 'build', 'venv', 'env', '__pycache__', '.next', '.vscode', 'vendor', '.idea'}
SUPPORTED_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.php',
        '.html', '.css', '.scss', '.json', '.yaml', '.yml', '.xml', '.md', '.Rmd', '.ipynb'
    }


def read_repo_files(repo_path: str) -> list[dict]:
    """Read all supported code files from repository directory."""
    files = []
    root_path = Path(repo_path)
    
    if not root_path.exists():
        return []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        
        for filename in filenames:
            if Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS:
                full_path = Path(dirpath) / filename
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        files.append({
                            "path": str(full_path.relative_to(root_path)),
                            "content": f.read()
                        })
                except (UnicodeDecodeError, IOError):
                    continue
    
    return files

def save_files_to_json(files: list[dict], output_path: str) -> None:
    """Save files to JSON format."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(files, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving JSON: {e}")

    
# Example usage:
# repo_data = read_repo_files("/home/rhinks/Desktop/projects/knowthecode/ingestion/cloned_repos/flask")
# save_files_to_json(repo_data, "output.json")