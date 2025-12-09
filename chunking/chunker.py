# chunker.py
import os
import sys
import json
import hashlib
import bisect
from typing import List, Dict, Optional

# Optional import: tree_sitter may not be installed or languages not built.
try:
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except Exception:
    TREE_SITTER_AVAILABLE = False

# -------- CONFIG --------
# Languages we plan to support (adjust as you add grammars)
COMPILED_LANGS = {
    'python': 'python',
    'javascript': 'javascript',
    'typescript': 'typescript',
    'java': 'java',
    'html':'html',
    'css':'css'
}

# chunk size heuristics
MAX_CHARS = 3000
MIN_CHARS = 30
OVERLAP_LINES = 2

# extension -> simple language name
EXT_LANG = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.java': 'java', '.go': 'go', '.rs': 'rust',
    '.c': 'c', '.cpp': 'cpp', '.md': 'markdown',
    '.json': 'json', '.yml': 'yaml', '.yaml': 'yaml'
}

# -------- utilities --------
def detect_lang_from_path(path: str) -> Optional[str]:
    _, ext = os.path.splitext(path.lower())
    return EXT_LANG.get(ext)

def compute_line_starts(text: str):
    # returns list of byte offsets for each line start (0-indexed)
    line_starts = []
    pos = 0
    for line in text.splitlines(True):
        line_starts.append(pos)
        pos += len(line.encode('utf8'))
    return line_starts

def byte_to_line(byte_offset: int, line_starts: List[int]) -> int:
    idx = bisect.bisect_right(line_starts, byte_offset) - 1
    return max(0, idx)

def slice_lines(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    start_line = max(0, start_line)
    end_line = min(len(lines) - 1, end_line)
    if start_line > end_line:
        return ''
    return '\n'.join(lines[start_line:end_line+1]) + '\n'

def make_id(path: str, start_line: int, end_line: int, snippet: Optional[str] = None) -> str:
    h = hashlib.sha256()
    h.update(path.encode('utf8'))
    h.update(b'\x00')
    h.update(str(start_line).encode())
    h.update(b'\x00')
    h.update(str(end_line).encode())
    if snippet:
        h.update(b'\x00')
        h.update(snippet.encode('utf8')[:200])
    return h.hexdigest()

# -------- Tree-sitter setup (v0.20+ with pre-compiled wheels) --------
PARSER_BY_LANG: Dict[str, Parser] = {}

# Map language keys to their pre-compiled wheel module names
LANG_MODULES = {
    'python':( 'tree_sitter_python','python'),
    'typescript':( 'tree_sitter_typescript','typescript'),
    'javascript':( 'tree_sitter_javascript','javascript'),
    'java': ('tree_sitter_java','java'),
    'html':('tree_sitter_html','html'),
    'css':('tree_sitter_css','css')
}

def get_language_object(module_name: str, lang_key: str):
    """
    Dynamically get the Language object from a module.
    Handles variations in how different packages expose their language.
    """
    lang_module = __import__(module_name)
    
    # Special cases for packages with non-standard APIs
    if lang_key == 'typescript':
        return lang_module.language_typescript()
    
    # Default: try .language()
    if hasattr(lang_module, 'language'):
        return lang_module.language()
    
    # If nothing works, raise an error
    raise AttributeError(f"Could not find language() in {module_name}")

if TREE_SITTER_AVAILABLE:
    print("DEBUG: tree_sitter available. Loading pre-compiled language wheels...")
    for lang_key, lang_name in COMPILED_LANGS.items():
        lang_info = LANG_MODULES.get(lang_key)
        if not lang_info:
            print(f"DEBUG: no module mapping for {lang_key}; skipping.")
            continue
        
        # Extract module name and display name from tuple
        module_name, display_name = lang_info
        
        try:
            # Get the language capsule from the module
            lang_capsule = get_language_object(module_name, lang_key)
            print(f"DEBUG: imported {module_name}")
            
            # Wrap capsule in Language object (v0.25 takes only 1 arg)
            lang = Language(lang_capsule)
            
            # Create parser with Language object (v0.25+ Constructor takes language)
            p = Parser(lang)
            PARSER_BY_LANG[lang_key] = p
            print(f"DEBUG: loaded parser for {lang_key} from {module_name}")
        except ImportError as e:
            print(f"DEBUG: {module_name} not installed for {lang_key}: {e}")
        except Exception as e:
            print(f"DEBUG: failed to load parser for {lang_key}: {e}")
    
    if PARSER_BY_LANG:
        print(f"DEBUG: successfully loaded {len(PARSER_BY_LANG)} parsers: {list(PARSER_BY_LANG.keys())}")
    else:
        print("DEBUG: no parsers loaded; fallback chunkers will be used for all files.")
else:
    print("DEBUG: tree_sitter Python binding NOT available; using fallback chunkers only.")

# -------- node selection heuristics (simple) --------
def select_nodes_for_lang(root_node, lang_name: str):
    wanted = set()
    ln = lang_name.lower()
    if ln == 'python':
        wanted = {'function_definition', 'class_definition', 'module'}
    elif ln in ('javascript', 'typescript'):
        wanted = {'function_declaration', 'class_declaration', 'program', 'method_definition', 'lexical_declaration', 'export_statement'}
    elif ln == 'java':
        wanted = {'class_declaration', 'method_declaration', 'program'}
    else:
        wanted = {'program'}
    results = []
    def walk(node):
        try:
            t = node.type
        except Exception:
            return
        if t in wanted:
            results.append(node)
            return
        for ch in getattr(node, "children", []):
            walk(ch)
    walk(root_node)
    return results

# -------- AST chunker (Tree-sitter) --------
def ast_chunk_file(path: str, content: str, lang: str) -> List[Dict]:
    if lang not in PARSER_BY_LANG:
        return []
    parser = PARSER_BY_LANG[lang]
    try:
        tree = parser.parse(content.encode('utf8'))
    except Exception:
        return []
    root = tree.root_node
    line_starts = compute_line_starts(content)
    nodes = select_nodes_for_lang(root, lang)
    chunks = []
    prev_chunk = None
    for node in nodes:
        sbyte = node.start_byte
        ebyte = node.end_byte
        start_line = byte_to_line(sbyte, line_starts)
        end_line = byte_to_line(max(0, ebyte-1), line_starts)
        sline = max(0, start_line - OVERLAP_LINES)
        eline = end_line + OVERLAP_LINES
        text = slice_lines(content, sline, eline)
        # merge tiny to previous
        if len(text) < MIN_CHARS and prev_chunk:
            prev_chunk['text'] = prev_chunk['text'] + '\n' + text
            prev_chunk['end_line'] = eline + 1
            prev_chunk['id'] = make_id(path, prev_chunk['start_line'], prev_chunk['end_line'], prev_chunk['text'][:200])
            continue
        # big: split by lines
        if len(text) > MAX_CHARS:
            lines = text.splitlines()
            i = 0
            while i < len(lines):
                j = i
                block = []
                while j < len(lines) and len('\n'.join(block)) < MAX_CHARS:
                    block.append(lines[j]); j += 1
                block_text = '\n'.join(block) + '\n'
                sline_block = sline + i
                eline_block = sline + j - 1
                ch = {
                    'id': make_id(path, sline_block+1, eline_block+1, block_text[:200]),
                    'file_path': path,
                    'start_line': sline_block+1,
                    'end_line': eline_block+1,
                    'text': block_text,
                    'lang': lang,
                    'is_fallback': False
                }
                chunks.append(ch)
                prev_chunk = ch
                i = j - OVERLAP_LINES if (j - OVERLAP_LINES) > i else j
        else:
            ch = {
                'id': make_id(path, sline+1, eline+1, text[:200]),
                'file_path': path,
                'start_line': sline+1,
                'end_line': eline+1,
                'text': text,
                'lang': lang,
                'is_fallback': False
            }
            chunks.append(ch)
            prev_chunk = ch
    return chunks

# -------- Fallback chunkers --------
def fallback_chunk_markdown(path: str, content: str) -> List[Dict]:
    lines = content.splitlines()
    chunks = []
    cur_lines = []
    cur_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('#'):
            if cur_lines:
                txt = '\n'.join(cur_lines) + '\n'
                chunks.append({
                    'id': make_id(path, cur_start+1, i, txt[:200]),
                    'file_path': path,
                    'start_line': cur_start+1,
                    'end_line': i,
                    'text': txt,
                    'lang': 'markdown',
                    'is_fallback': True
                })
            cur_lines = [line]
            cur_start = i
        else:
            cur_lines.append(line)
    if cur_lines:
        txt = '\n'.join(cur_lines) + '\n'
        chunks.append({
            'id': make_id(path, cur_start+1, len(lines), txt[:200]),
            'file_path': path,
            'start_line': cur_start+1,
            'end_line': len(lines),
            'text': txt,
            'lang': 'markdown',
            'is_fallback': True
        })
    return chunks

def fallback_chunk_json(path: str, content: str) -> List[Dict]:
    try:
        obj = json.loads(content)
    except Exception:
        return fallback_chunk_generic(path, content)
    chunks = []
    if isinstance(obj, dict):
        for i, (k, v) in enumerate(obj.items()):
            body = json.dumps({k: v}, indent=2)
            chunks.append({
                'id': make_id(path, i+1, i+1, body[:200]),
                'file_path': path,
                'start_line': i+1,
                'end_line': i+1,
                'text': body + '\n',
                'lang': 'json',
                'is_fallback': True
            })
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            body = json.dumps(item, indent=2)
            chunks.append({
                'id': make_id(path, i+1, i+1, body[:200]),
                'file_path': path,
                'start_line': i+1,
                'end_line': i+1,
                'text': body + '\n',
                'lang': 'json',
                'is_fallback': True
            })
    else:
        chunks.append({
            'id': make_id(path, 1, 1, content[:200]),
            'file_path': path,
            'start_line': 1,
            'end_line': 1,
            'text': content,
            'lang': 'json',
            'is_fallback': True
        })
    return chunks

def fallback_chunk_generic(path: str, content: str) -> List[Dict]:
    lines = content.splitlines()
    if not lines:
        return []
    chunks = []
    i = 0
    n = len(lines)
    while i < n:
        j = i
        block = []
        while j < n and len('\n'.join(block)) < MAX_CHARS:
            block.append(lines[j]); j += 1
        text = '\n'.join(block) + '\n'
        chunks.append({
            'id': make_id(path, i+1, j, text[:200]),
            'file_path': path,
            'start_line': i+1,
            'end_line': j,
            'text': text,
            'lang': detect_lang_from_path(path) or 'text',
            'is_fallback': True
        })
        i = j - OVERLAP_LINES if (j - OVERLAP_LINES) > i else j
    return chunks

# -------- main chunk dispatcher --------
def chunk_file_entry(entry: Dict) -> List[Dict]:
    path = entry.get('path', '<unknown>')
    content = entry.get('content', '')
    lang = detect_lang_from_path(path)
    chunks = []
    if lang and lang in PARSER_BY_LANG:
        try:
            chunks = ast_chunk_file(path, content, lang)
        except Exception:
            chunks = []
    if not chunks:
        if (path.lower().endswith('.md') or lang == 'markdown'):
            chunks = fallback_chunk_markdown(path, content)
        elif (path.lower().endswith('.json') or lang == 'json'):
            chunks = fallback_chunk_json(path, content)
        else:
            chunks = fallback_chunk_generic(path, content)
    if not chunks:
        chunks = [{
            'id': make_id(path, 1, 1, content[:200]),
            'file_path': path,
            'start_line': 1,
            'end_line': max(1, len(content.splitlines())),
            'text': content,
            'lang': lang or 'unknown',
            'is_fallback': True
        }]
    return chunks

def process_files(entries: List[Dict]) -> List[Dict]:
    out = []
    for e in entries:
        chs = chunk_file_entry(e)
        out.extend(chs)
    return out

# -------- CLI usage --------
def main():
    if len(sys.argv) < 2:
        print("Usage: python chunker.py <input_json_file_or_dir> [output.json]")
        sys.exit(1)
    inp = sys.argv[1]
    outp = sys.argv[2] if len(sys.argv) > 2 else "chunks.json"
    entries = []
    if os.path.isdir(inp):
        # read all text files (simple)
        for root, _, files in os.walk(inp):
            for fn in files:
                fp = os.path.join(root, fn)
                try:
                    with open(fp, 'r', encoding='utf8') as fh:
                        rel = os.path.relpath(fp, inp)
                        entries.append({'path': rel, 'content': fh.read()})
                except Exception:
                    continue
    else:
        with open(inp, 'r', encoding='utf8') as fh:
            entries = json.load(fh)
    chunks = process_files(entries)
    with open(outp, 'w', encoding='utf8') as fh:
        json.dump(chunks, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {len(chunks)} chunks to {outp}")
    # helpful debug: show loaded parsers
    try:
        print("Loaded parsers:", list(PARSER_BY_LANG.keys()))
    except Exception:
        pass

if __name__ == "__main__":
    main()
