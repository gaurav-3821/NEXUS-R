"""VectorStore — persistent ChromaDB wrapper for semantic memory search."""

from __future__ import annotations

import os
import uuid

import chromadb
from chromadb.config import Settings


class VectorStore:
    """Persistent ChromaDB-backed vector store for fact embeddings.

    Stores each fact as a ChromaDB document keyed by fact_id for semantic
    retrieval via ``query_facts()``.
    """

    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "memory_facts") -> None:
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_fact(self, fact_id: str, text: str) -> None:
        """Embed and store a single fact in the vector index."""
        if not text.strip():
            return
        self._collection.add(
            documents=[text],
            ids=[fact_id],
        )

    def add_facts_bulk(self, facts: list[tuple[str, str]]) -> None:
        """Embed and store multiple facts in one batch.

        Each tuple is ``(fact_id, text)``.
        """
        valid = [(fid, txt) for fid, txt in facts if txt.strip()]
        if not valid:
            return
        self._collection.add(
            documents=[t for _, t in valid],
            ids=[fid for fid, _ in valid],
        )

    def query_facts(self, query: str, n_results: int = 3) -> list[str]:
        """Return the top-``n_results`` fact IDs most semantically similar to ``query``."""
        if not query.strip():
            return []
        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count() or 1),
        )
        if results and results["ids"]:
            return results["ids"][0]
        return []

    def delete_fact(self, fact_id: str) -> None:
        """Remove a fact from the vector index by its ID."""
        try:
            self._collection.delete(ids=[fact_id])
        except Exception:
            pass

    def delete_facts_by_ids(self, fact_ids: set[str]) -> None:
        """Remove multiple facts from the vector index."""
        try:
            self._collection.delete(ids=list(fact_ids))
        except Exception:
            pass

    def reset(self) -> None:
        """Remove all documents from the collection."""
        try:
            ids = self._collection.get()["ids"]
            if ids:
                self._collection.delete(ids=ids)
        except Exception:
            pass

    def count(self) -> int:
        return self._collection.count()
