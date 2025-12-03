import tempfile
import git
import os


def ingest_repo(repo_url) -> str:
    """
    Clone the repo to a temporary folder and return the local repo_path.
    Crawling / reading files is handled by read_repo_files().
    """


