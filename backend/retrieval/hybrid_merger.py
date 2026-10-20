from typing import List, Dict, Any, Optional
import concurrent.futures
from sentence_transformers import CrossEncoder
from backend.retrieval.vector_retriever import VectorRetriever
from backend.retrieval.graph_retriever import GraphRetriever
from backend.config import settings

class HybridMerger:
    """
    Orchestrates Hybrid Retrieval by:
    1. Running Dense Vector Retrieval and Graph Traversal Retrieval concurrently
    2. Deduplicating overlapping retrieved chunks by chunk_id
    3. Reranking candidates using CrossEncoder (ms-marco-MiniLM-L-6-v2)
    4. Selecting top_k grounded chunks and packaging the traversed subgraph
    """

    def __init__(self, vector_retriever: VectorRetriever, graph_retriever: GraphRetriever):
        self.vector_retriever = vector_retriever
        self.graph_retriever = graph_retriever
        self._cross_encoder = None

    @property
    def cross_encoder(self) -> Optional[CrossEncoder]:
        if self._cross_encoder is None:
            try:
                self._cross_encoder = CrossEncoder(settings.reranker_model_name)
            except Exception as e:
                print(f"Notice: CrossEncoder load failed, will use weighted heuristic reranker: {e}")
                self._cross_encoder = False
        return self._cross_encoder if self._cross_encoder is not False else None

    def retrieve(self, query: str, top_k: int = 6) -> Dict[str, Any]:
        """
        Executes parallel hybrid retrieval and cross-encoder reranking.
        """
        # Execute retrievers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_vec = executor.submit(self.vector_retriever.retrieve, query, 10)
            future_graph = executor.submit(self.graph_retriever.retrieve, query, settings.graph_retrieval_depth)

            vec_chunks = future_vec.result()
            graph_res = future_graph.result()

        graph_chunks = graph_res.get("chunks", [])
        subgraph = graph_res.get("subgraph", {})

        # Deduplicate chunks
        merged_chunks: Dict[str, Dict[str, Any]] = {}

        # Ingest vector chunks
        for c in vec_chunks:
            c_id = c["chunk_id"]
            merged_chunks[c_id] = {
                **c,
                "vector_score": c.get("score", 0.0),
                "graph_score": 0.0,
                "sources": ["vector"]
            }

        # Ingest graph chunks
        for c in graph_chunks:
            c_id = c["chunk_id"]
            if c_id in merged_chunks:
                merged_chunks[c_id]["graph_score"] = c.get("score", 0.8)
                merged_chunks[c_id]["sources"].append("graph")
            else:
                merged_chunks[c_id] = {
                    **c,
                    "vector_score": 0.0,
                    "graph_score": c.get("score", 0.8),
                    "sources": ["graph"]
                }

        candidate_list = list(merged_chunks.values())
        if not candidate_list:
            return {
                "chunks": [],
                "subgraph": subgraph,
                "retrieval_mode": "hybrid"
            }

        # Rerank candidates
        reranked_chunks = self._rerank(query, candidate_list, top_k=top_k)

        return {
            "chunks": reranked_chunks,
            "subgraph": subgraph,
            "retrieval_mode": "hybrid",
            "stats": {
                "vector_candidates": len(vec_chunks),
                "graph_candidates": len(graph_chunks),
                "deduplicated_count": len(candidate_list),
                "final_count": len(reranked_chunks)
            }
        }

    def _rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
        """Reranks candidates using Cross-Encoder or blended score heuristic."""
        ce = self.cross_encoder
        if ce:
            try:
                pairs = [[query, c["text"]] for c in candidates]
                scores = ce.predict(pairs)
                for idx, c in enumerate(candidates):
                    c["rerank_score"] = float(scores[idx])
                candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
                return candidates[:top_k]
            except Exception as e:
                print(f"Error in cross-encoder predict: {e}")

        # Fallback blended heuristic: 0.6 * vector_score + 0.4 * graph_score + boost for dual presence
        for c in candidates:
            v_score = c.get("vector_score", 0.0)
            g_score = c.get("graph_score", 0.0)
            dual_boost = 0.2 if len(c.get("sources", [])) > 1 else 0.0
            c["rerank_score"] = (0.5 * v_score) + (0.5 * g_score) + dual_boost

        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return candidates[:top_k]
