"""
Embeddings — Local sentence-transformers for vector embeddings.

Uses all-MiniLM-L6-v2 by default (free, fast, runs on CPU).
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid slow startup
_model = None
_model_name = None


def _get_model(model_name: str = "all-MiniLM-L6-v2"):
    """Lazy-load the sentence transformer model."""
    global _model, _model_name
    if _model is None or _model_name != model_name:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", model_name)
            _model = SentenceTransformer(model_name)
            _model_name = model_name
            logger.info("Embedding model loaded (%d dims)", _model.get_sentence_embedding_dimension())
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )
    return _model


def embed_texts(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
    show_progress: bool = False,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.

    Returns list of float vectors (384-dim for MiniLM).
    """
    model = _get_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
    )
    return embeddings.tolist()


def embed_query(
    query: str,
    model_name: str = "all-MiniLM-L6-v2",
) -> List[float]:
    """Generate embedding for a single query string."""
    result = embed_texts([query], model_name=model_name)
    return result[0]


def get_embedding_dimension(model_name: str = "all-MiniLM-L6-v2") -> int:
    """Get the embedding dimension for the model."""
    model = _get_model(model_name)
    return model.get_sentence_embedding_dimension()
