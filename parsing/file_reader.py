def read_repo_files(repo_path: str) -> list[dict]:
    """
    Recursively walks the repo directory and returns a list of files to process.
    - Skips folders like .git, node_modules, dist, build, etc.
    - Keeps only relevant file types (code + docs).
    Returns: [{"path": str, "content": str}, ...]
    """
