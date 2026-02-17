"""
RAG Tools — Query and ingest documents into the knowledge base.
"""

import logging
from typing import Dict, Any, Optional

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Pipeline instance set during server startup
_rag_pipeline = None


def set_rag_pipeline(pipeline):
    """Inject the RAG pipeline instance (called during server init)."""
    global _rag_pipeline
    _rag_pipeline = pipeline


class RAGQueryTool(BaseTool):
    """Search the knowledge base for relevant information."""

    name = "rag_query"
    description = "Search the knowledge base (documents, PDFs, notes) for information relevant to a question. Use this when the user asks about their uploaded documents or stored knowledge."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question or search query to find relevant documents",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)

        if not query:
            return "Error: No query provided."

        if not _rag_pipeline:
            return "Knowledge base not initialized. No documents have been ingested yet."

        try:
            result = _rag_pipeline.query(query, top_k=top_k)
            return result
        except Exception as e:
            return f"Error querying knowledge base: {e}"


class RAGIngestTool(BaseTool):
    """Add documents to the knowledge base."""

    name = "rag_ingest"
    description = "Add a file or text to the knowledge base for future retrieval. Supports text, markdown, Python, and PDF files."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to a file to ingest (text, markdown, code, or PDF)",
                },
                "text": {
                    "type": "string",
                    "description": "Raw text to add to the knowledge base (use this OR file_path)",
                },
                "source": {
                    "type": "string",
                    "description": "Source label for the ingested content (default: filename or 'direct_input')",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs) -> str:
        file_path = kwargs.get("file_path", "")
        text = kwargs.get("text", "")
        source = kwargs.get("source", "")

        if not _rag_pipeline:
            return "Knowledge base not initialized."

        if not file_path and not text:
            return "Error: Provide either 'file_path' or 'text' to ingest."

        try:
            if file_path:
                count = _rag_pipeline.ingest_file(file_path)
                return f"Successfully ingested '{file_path}' → {count} chunks added to knowledge base."
            else:
                source = source or "direct_input"
                count = _rag_pipeline.ingest_text(text, source=source)
                return f"Successfully ingested text ({len(text)} chars) → {count} chunks added."

        except FileNotFoundError:
            return f"Error: File not found: {file_path}"
        except Exception as e:
            return f"Error ingesting content: {e}"
