import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from backend.config import settings

class ChromaEmbedder:
    """
    Manages vector embeddings and storage in ChromaDB using local SentenceTransformers.
    """

    def __init__(self, persist_dir: Optional[Path] = None, model_name: Optional[str] = None):
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.model_name = model_name or settings.embedding_model_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._model = None
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self._client.get_or_create_collection(
            name="sebi_rbi_regulatory_chunks",
            metadata={"hnsw:space": "cosine"}
        )

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                # Fallback to lightweight model if primary is unavailable
                self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of strings."""
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Embeds and stores chunks into ChromaDB.
        """
        if not chunks:
            return 0

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "document_name": c["document_name"],
                "regulator": c["regulator"],
                "circular_code": c["circular_code"],
                "circular_date": c["circular_date"],
                "page_number": c["page_number"],
                "chunk_index": c["chunk_index"]
            }
            for c in chunks
        ]

        embeddings = self.embed_texts(documents)

        # Batch upsert into ChromaDB
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end_idx = i + batch_size
            self.collection.upsert(
                ids=ids[i:end_idx],
                embeddings=embeddings[i:end_idx],
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )

        return len(ids)

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Runs dense vector query against ChromaDB.
        """
        query_emb = self.embed_texts([query_text])[0]
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        retrieved: List[Dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return retrieved

        for idx in range(len(results["ids"][0])):
            retrieved.append({
                "chunk_id": results["ids"][0][idx],
                "text": results["documents"][0][idx],
                "metadata": results["metadatas"][0][idx],
                "score": float(1 - results["distances"][0][idx]) if results["distances"] else 0.0
            })

        return retrieved

    def get_total_chunks(self) -> int:
        return self.collection.count()
