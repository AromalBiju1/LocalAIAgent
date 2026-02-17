"""
RAG Pipeline — Orchestrates document ingestion and retrieval.

Flow: ingest → chunk → embed → store → retrieve
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.rag.chunker import chunk_text, chunk_file, TextChunk
from src.rag.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """End-to-end RAG pipeline for document Q&A."""

    def __init__(
        self,
        persist_dir: str = "data/vectorstore",
        collection_name: str = "documents",
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        top_k: int = 5,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

        self.vectorstore = VectorStore(
            persist_dir=persist_dir,
            collection_name=collection_name,
            embedding_model=embedding_model,
        )

    # ── Ingest ────────────────────────────────────────────

    def ingest_file(self, file_path: str) -> int:
        """
        Ingest a file into the vector store.

        Args:
            file_path: Path to any text/code/PDF file.

        Returns:
            Number of chunks added.
        """
        logger.info("Ingesting file: %s", file_path)
        chunks = chunk_file(
            file_path,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        if not chunks:
            logger.warning("No chunks generated from %s", file_path)
            return 0

        texts = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]

        return self.vectorstore.add_documents(texts, metadatas=metadatas)

    def ingest_text(self, text: str, source: str = "direct_input") -> int:
        """
        Ingest raw text into the vector store.

        Args:
            text: Raw text to ingest.
            source: Source identifier.

        Returns:
            Number of chunks added.
        """
        chunks = chunk_text(
            text,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            source=source,
        )

        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]

        return self.vectorstore.add_documents(texts, metadatas=metadatas)

    def ingest_directory(self, dir_path: str, extensions: Optional[List[str]] = None) -> int:
        """
        Ingest all matching files from a directory.

        Args:
            dir_path: Directory to scan.
            extensions: File extensions to include (default: common text/code types).

        Returns:
            Total chunks added.
        """
        if extensions is None:
            extensions = [".txt", ".md", ".py", ".js", ".ts", ".pdf", ".rst", ".csv"]

        path = Path(dir_path)
        if not path.is_dir():
            raise ValueError(f"Not a directory: {dir_path}")

        total = 0
        for ext in extensions:
            for file in path.rglob(f"*{ext}"):
                try:
                    total += self.ingest_file(str(file))
                except Exception as e:
                    logger.warning("Failed to ingest %s: %s", file, e)

        logger.info("Ingested %d chunks from directory %s", total, dir_path)
        return total

    # ── Retrieve ──────────────────────────────────────────

    def query(self, question: str, top_k: Optional[int] = None) -> str:
        """
        Retrieve relevant context for a question.

        Args:
            question: User's question.
            top_k: Override number of results.

        Returns:
            Formatted context string for the LLM.
        """
        k = top_k or self.top_k
        results = self.vectorstore.search(question, top_k=k)

        if not results:
            return "No relevant documents found in the knowledge base."

        context_parts = []
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source", "unknown")
            score = r["score"]
            context_parts.append(
                f"[{i}] (source: {source}, relevance: {score:.0%})\n{r['content']}"
            )

        return "\n\n---\n\n".join(context_parts)

    def search_raw(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return raw search results (for API use)."""
        return self.vectorstore.search(query, top_k=top_k or self.top_k)

    # ── Stats ─────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Pipeline statistics."""
        vs_stats = self.vectorstore.stats()
        return {
            **vs_stats,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
        }
