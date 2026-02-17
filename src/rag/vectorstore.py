"""
Vector Store — FAISS-backed persistent vector storage.

Lightweight vector similarity search using FAISS with JSON metadata sidecar.
No external server needed — just numpy arrays on disk.
"""

import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-backed vector store for RAG retrieval."""

    def __init__(
        self,
        persist_dir: str = "data/vectorstore",
        collection_name: str = "documents",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        # In-memory state
        self._index = None          # FAISS index
        self._documents: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        self._ids: List[str] = []

        self._init_store()

    # ── File paths ────────────────────────────────────────

    @property
    def _index_path(self) -> Path:
        return self.persist_dir / f"{self.collection_name}.faiss"

    @property
    def _meta_path(self) -> Path:
        return self.persist_dir / f"{self.collection_name}.json"

    # ── Init / Load / Save ────────────────────────────────

    def _init_store(self):
        """Initialize FAISS index, loading from disk if available."""
        try:
            import faiss  # noqa: F401
        except ImportError:
            raise RuntimeError("faiss-cpu not installed. Run: pip install faiss-cpu")

        self.persist_dir.mkdir(parents=True, exist_ok=True)

        if self._index_path.exists() and self._meta_path.exists():
            self._load()
        else:
            # Will be created on first add (need to know dimension)
            self._index = None

        doc_count = len(self._documents)
        logger.info(
            "VectorStore ready: collection='%s', docs=%d",
            self.collection_name, doc_count,
        )

    def _load(self):
        """Load index and metadata from disk."""
        import faiss

        self._index = faiss.read_index(str(self._index_path))

        with open(self._meta_path, "r") as f:
            meta = json.load(f)

        self._documents = meta.get("documents", [])
        self._metadatas = meta.get("metadatas", [])
        self._ids = meta.get("ids", [])
        logger.info("Loaded %d documents from disk", len(self._documents))

    def _save(self):
        """Persist index and metadata to disk."""
        import faiss

        if self._index is not None:
            faiss.write_index(self._index, str(self._index_path))

        with open(self._meta_path, "w") as f:
            json.dump({
                "documents": self._documents,
                "metadatas": self._metadatas,
                "ids": self._ids,
            }, f)

    # ── Add documents ─────────────────────────────────────

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> int:
        """
        Add documents with their embeddings to the store.

        Args:
            texts: List of text chunks to add.
            metadatas: Optional metadata for each chunk.
            ids: Optional unique IDs (auto-generated if not provided).

        Returns:
            Number of documents added.
        """
        if not texts:
            return 0

        import faiss
        from src.rag.embeddings import embed_texts

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4())[:12] for _ in texts]

        # Generate embeddings
        embeddings = embed_texts(texts, model_name=self.embedding_model)
        vectors = np.array(embeddings, dtype=np.float32)

        # Normalise for cosine similarity (use inner product after normalisation)
        faiss.normalize_L2(vectors)

        # Create index on first add
        if self._index is None:
            dim = vectors.shape[1]
            self._index = faiss.IndexFlatIP(dim)  # Inner product = cosine after L2 norm

        # Add to index
        self._index.add(vectors)

        # Store metadata
        self._documents.extend(texts)
        self._metadatas.extend(metadatas or [{}] * len(texts))
        self._ids.extend(ids)

        # Persist
        self._save()

        logger.info("Added %d documents to vector store", len(texts))
        return len(texts)

    # ── Search ────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            where: Optional metadata filter (applied post-search).

        Returns:
            List of results with 'content', 'metadata', and 'score'.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        import faiss
        from src.rag.embeddings import embed_query

        query_embedding = embed_query(query, model_name=self.embedding_model)
        query_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_vec, k)

        output = []
        for i, idx in enumerate(indices[0]):
            if idx < 0:
                continue
            meta = self._metadatas[idx] if idx < len(self._metadatas) else {}

            # Apply metadata filter if provided
            if where:
                if not all(meta.get(wk) == wv for wk, wv in where.items()):
                    continue

            output.append({
                "content": self._documents[idx],
                "metadata": meta,
                "score": round(float(scores[0][i]), 4),
                "id": self._ids[idx] if idx < len(self._ids) else "",
            })

        return output

    # ── Management ────────────────────────────────────────

    def count(self) -> int:
        """Number of documents in the store."""
        return len(self._documents)

    def delete(self, ids: List[str]):
        """Delete documents by ID (rebuilds index)."""
        import faiss

        keep = [i for i, doc_id in enumerate(self._ids) if doc_id not in set(ids)]
        if len(keep) == len(self._ids):
            return  # Nothing to delete

        self._documents = [self._documents[i] for i in keep]
        self._metadatas = [self._metadatas[i] for i in keep]
        self._ids = [self._ids[i] for i in keep]

        # Rebuild index from remaining embeddings
        if self._documents:
            from src.rag.embeddings import embed_texts
            embeddings = embed_texts(self._documents, model_name=self.embedding_model)
            vectors = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(vectors)
            dim = vectors.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(vectors)
        else:
            self._index = None

        self._save()
        logger.info("Deleted %d documents, %d remaining", len(ids) - len(keep), len(self._documents))

    def clear(self):
        """Delete all documents."""
        self._index = None
        self._documents = []
        self._metadatas = []
        self._ids = []

        # Remove files
        if self._index_path.exists():
            self._index_path.unlink()
        if self._meta_path.exists():
            self._meta_path.unlink()

        logger.info("Vector store cleared")

    def stats(self) -> Dict[str, Any]:
        """Store statistics."""
        return {
            "collection": self.collection_name,
            "document_count": self.count(),
            "embedding_model": self.embedding_model,
            "persist_dir": str(self.persist_dir),
            "index_size": self._index.ntotal if self._index else 0,
        }
