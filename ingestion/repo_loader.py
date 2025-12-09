from pathlib import Path
from git import Repo
import shutil

def get_repo_name_from_url(repo_url: str) -> str:
    """
    Extracts repo name from a GitHub URL.
    Example: https://github.com/user/test.git -> test
    """
    name = repo_url.rstrip("/").split("/")[-1]
    return name.replace(".git", "")

def ingest_repo(repo_url: str) -> Path:
    base_dir = Path(__file__).resolve().parent / "cloned_repos"
    base_dir.mkdir(parents=True, exist_ok=True)

    repo_name = get_repo_name_from_url(repo_url)
    repo_dir = base_dir / repo_name

    # delete old clone if it exists
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    print("Cloning into:", repo_dir)
    Repo.clone_from(repo_url, repo_dir)
    print("Repository cloned successfully.")

    return repo_dir


cloned_location = ingest_repo("https://github.com/forzzzzz/Calculator-You.git")
print(cloned_location)
