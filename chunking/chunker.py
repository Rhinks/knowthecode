def chunk_files(files: list[dict]) -> list[dict]:
    """
    Split files into semantically meaningful chunks (ideally using Tree-sitter/AST).
    Input: [{"path": str, "content": str}, ...]
    Output: list of chunks like:
        {
            "id": str,          # unique chunk ID
            "file_path": str,
            "start_line": int,  # optional
            "end_line": int,    # optional
            "text": str         # chunk content
        }
    These chunks will be passed to the embedding step.
    """
