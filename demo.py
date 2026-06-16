"""Convenience wrapper for the canonical terminal demo.

Run from a fresh checkout with:
    python demo.py

After installing the project package, this also works:
    python -m rag_from_scratch.demo
"""

from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rag_from_scratch.demo import run_demo


if __name__ == "__main__":
    run_demo()
