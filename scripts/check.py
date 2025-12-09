# scripts/check_parsers.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from chunking import chunker
print("PARSERS LOADED:", list(chunker.PARSER_BY_LANG.keys()))
