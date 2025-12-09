import os
from pathlib import Path
from typing import List, Dict


IGNORED_DIRS = {'.git', 'node_modules', 'dist', 'build', 'venv', 'env', '__pycache__', '.next', '.vscode', 'vendor', '.idea'}
SUPPORTED_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.php',
        '.html', '.css', '.scss', '.json', '.yaml', '.yml', '.xml', '.md', '.Rmd', '.ipynb'
    }


def folder_exists(last_folder):
    base = os.path.abspath("../ingestion/cloned_repos")
    return os.path.isdir(os.path.join(base, last_folder))

def read_files(repo_path):
    files_to_process = []
    root_path=Path(repo_path)

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        
        for filename in filenames:
            file_extension = Path(filename).suffix.lower()

            if file_extension in SUPPORTED_EXTENSIONS:
                full_path = Path(dirpath) / filename

                try:
                    with open(full_path, 'r',encoding='utf-8') as f:
                        content = f.read()
                        files_to_process.append({
                            "path":str(full_path.relative_to(root_path)),
                            "content":content
                        })
                except UnicodeDecodeError as e:
                    print(f"skipping file due to coding error : {e}")
                except IOError as e:
                    print(f"Error reading file {full_path} : {e}")

    return files_to_process



def read_repo_files(repo_path: str) -> list[dict]:
    """
    Recursively walks the repo directory and returns a list of files to process.
    - Skips folders like .git, node_modules, dist, build, etc.
    - Keeps only relevant file types (code + docs).
    Returns: [{"path": str, "content": str}, ...]
    """
    repo_name = os.path.basename(repo_path)

    if folder_exists(repo_name):
        return read_files(repo_path)
    else:
        print("Folder does NOT exists")

    
#now call it from main.py like file_reader.py(repo_path)

repo_data = read_repo_files("/home/rhinks/Desktop/projects/knowthecode/ingestion/cloned_repos/Calculator-You")
print((repo_data))