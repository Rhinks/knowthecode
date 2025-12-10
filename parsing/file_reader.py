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
    """
    Recursively walks the repo directory and returns a list of files to process.
    - Skips folders like .git, node_modules, dist, build, etc.
    - Keeps only relevant file types (code + docs).
    Returns: [{"path": str, "content": str}, ...]
    """
    files_to_process = []
    root_path = Path(repo_path)
    
    # Check if path exists
    if not root_path.exists():
        print(f"ERROR: Path does not exist: {repo_path}")
        return []
    
    print(f"DEBUG: Reading files from {repo_path}")
    file_count = 0
    skipped_encoding = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        
        for filename in filenames:
            file_extension = Path(filename).suffix.lower()

            # Check if extension is supported
            if file_extension in SUPPORTED_EXTENSIONS:
                full_path = Path(dirpath) / filename

                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files_to_process.append({
                            "path": str(full_path.relative_to(root_path)),
                            "content": content
                        })
                    file_count += 1
                except UnicodeDecodeError:
                    print(f"DEBUG: Skipped {full_path} (encoding error)")
                    skipped_encoding += 1
                except IOError as e:
                    print(f"DEBUG: Skipped {full_path} (IO error)")
    
    print(f"DEBUG: Successfully read {file_count} files ({skipped_encoding} skipped due to encoding)")
    return files_to_process

def save_files_to_json(files: list[dict], output_path: str) -> None:
    """
    Save file list to JSON format (UTF-8 encoded, properly escaped).
    Args:
        files: list of dicts with 'path' and 'content'
        output_path: path to output .json file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(files, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(files)} files to {output_path}")
    except Exception as e:
        print(f"Error saving JSON: {e}")

    
# Example usage:
repo_data = read_repo_files("/home/rhinks/Desktop/projects/knowthecode/ingestion/cloned_repos/flask")
save_files_to_json(repo_data, "output.json")