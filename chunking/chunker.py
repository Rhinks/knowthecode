
"""
IMPORTANT NODES FOR CHUNKING 

function_declaration
method_definition
arrow_function (sometimes)
class_declaration
export_statement 
lexical_declaration (for constants)
import_statement

METADATA FIELDS:

path               → file path
language           → python / ts / java
type               → function/class/method/module
start_line         → for UI
end_line           → for UI
chunk_id           → unique ID
content            → the actual text
"""



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

    #figure out the extension.
    #parse using tree sitter - good for almost every language. for now skip language specific parsingg
    #fall back to file level chunkingg if parsing fails or grammer not available 
    #

