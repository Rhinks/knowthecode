from pathlib import Path
from git import Repo
import shutil

def get_repo_name_from_url(repo_url: str) -> str:
    """Extract repository name from GitHub URL."""
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")

def ingest_repo(repo_url: str) -> Path:
    """Clone GitHub repository locally."""
    base_dir = Path(__file__).resolve().parent / "cloned_repos"
    base_dir.mkdir(parents=True, exist_ok=True)

    repo_name = get_repo_name_from_url(repo_url)
    repo_dir = base_dir / repo_name

    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    Repo.clone_from(repo_url, repo_dir)
    return repo_dir
