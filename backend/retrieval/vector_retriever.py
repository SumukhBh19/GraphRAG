from typing import List, Dict, Any
from backend.ingestion.embedder import ChromaEmbedder

class VectorRetriever:
    """
    Dense vector retriever using ChromaDB cosine similarity over embedded regulatory chunks.
    Serves as the baseline retriever in Vanilla RAG and one half of HybridRAG.
    """

    def __init__(self, embedder: ChromaEmbedder):
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves top_k nearest chunks for a given natural language query.
        """
        results = self.embedder.query(query_text=query, top_k=top_k)
        formatted = []
        for r in results:
            meta = r.get("metadata", {})
            formatted.append({
                "chunk_id": r["chunk_id"],
                "text": r["text"],
                "document_name": meta.get("document_name", "Unknown"),
                "circular_code": meta.get("circular_code", "Unknown"),
                "circular_date": meta.get("circular_date", "Unknown"),
                "page_number": meta.get("page_number", 1),
                "score": r.get("score", 0.0),
                "retrieval_source": "vector"
            })
        return formatted
