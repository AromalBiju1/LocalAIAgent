"""
Text Chunker — Split documents into overlapping chunks for RAG.

Supports plain text, markdown, code files, and PDFs.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TextChunk:
    """A chunk of text with metadata."""

    def __init__(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.metadata = metadata or {}

    def __repr__(self):
        return f"TextChunk({len(self.content)} chars, {self.metadata.get('source', '?')})"


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    source: str = "unknown",
) -> List[TextChunk]:
    """
    Split text into overlapping chunks.

    Args:
        text: Input text to chunk.
        chunk_size: Max characters per chunk.
        chunk_overlap: Overlap between consecutive chunks.
        source: Source identifier for metadata.

    Returns:
        List of TextChunk objects.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a natural boundary (paragraph, sentence, word)
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                for sep in [". ", "! ", "? ", "\n"]:
                    sent_break = text.rfind(sep, start, end)
                    if sent_break > start + chunk_size // 2:
                        end = sent_break + len(sep)
                        break
                else:
                    # Look for word break
                    word_break = text.rfind(" ", start, end)
                    if word_break > start + chunk_size // 2:
                        end = word_break + 1

        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append(TextChunk(
                content=chunk_content,
                metadata={
                    "source": source,
                    "chunk_index": chunk_idx,
                    "start_char": start,
                    "end_char": end,
                },
            ))
            chunk_idx += 1

        start = end - chunk_overlap
        if start >= len(text):
            break

    return chunks


def chunk_file(
    file_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[TextChunk]:
    """
    Read and chunk a file. Supports .txt, .md, .py, .js, .pdf, etc.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    source = path.name

    if ext == ".pdf":
        text = _read_pdf(path)
    elif ext in (".txt", ".md", ".rst", ".csv", ".log"):
        text = path.read_text(encoding="utf-8", errors="replace")
    elif ext in (".py", ".js", ".ts", ".tsx", ".java", ".c", ".cpp", ".go", ".rs", ".rb", ".sh"):
        text = path.read_text(encoding="utf-8", errors="replace")
        source = f"code:{path.name}"
    else:
        # Try reading as text
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Cannot read %s: %s", file_path, e)
            return []

    return chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap, source=source)


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF using pymupdf."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(str(path))
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n\n".join(pages)
    except ImportError:
        raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")
