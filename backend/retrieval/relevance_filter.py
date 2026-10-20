"""
Post-Retrieval Relevance Filter
================================
For each retrieved chunk, asks the LLM (Groq if available, heuristic otherwise):
  "Is this chunk relevant to answering the query? Answer yes or no."
Chunks that answer 'no' are dropped before context assembly.
"""

import re
from typing import List, Dict, Any, Optional


class PostRetrievalRelevanceFilter:
    """
    Filters retrieved chunks by relevance before passing them to the generator.
    Uses Groq LLM for accurate filtering when available, falls back to a
    keyword-overlap heuristic otherwise.
    """

    def __init__(self, groq_client=None, groq_model: str = "llama-3.1-8b-instant"):
        self.groq_client = groq_client
        self.groq_model = groq_model

    def filter_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        min_chunks: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Filters chunks for relevance. Always keeps at least min_chunks.
        
        Args:
            query: The user's question.
            chunks: Retrieved chunk dicts (must contain 'text').
            min_chunks: Minimum number of chunks to keep even if all fail.
        
        Returns:
            Filtered list of relevant chunks.
        """
        if not chunks:
            return chunks

        relevant = []
        for chunk in chunks:
            if self._is_relevant(query, chunk):
                relevant.append(chunk)

        # Always preserve at least min_chunks to avoid empty context
        if len(relevant) < min_chunks:
            # Keep the ones not yet in relevant, up to min_chunks total
            extras = [c for c in chunks if c not in relevant]
            relevant = relevant + extras[: min_chunks - len(relevant)]

        return relevant

    def _is_relevant(self, query: str, chunk: Dict[str, Any]) -> bool:
        """Returns True if the chunk is relevant to the query."""
        text = chunk.get("text", "").strip()
        if not text:
            return False

        if self.groq_client:
            return self._llm_relevance_check(query, text)
        else:
            return self._heuristic_relevance_check(query, text)

    def _llm_relevance_check(self, query: str, text: str) -> bool:
        """
        Uses Groq LLM to judge relevance. Expects 'yes' or 'no'.
        Falls back to heuristic on error.
        """
        prompt = (
            f"You are a regulatory document relevance judge.\n"
            f"Query: {query}\n\n"
            f"Document Chunk:\n{text[:800]}\n\n"
            f"Is this chunk relevant to answering the query? "
            f"Answer with only 'yes' or 'no'."
        )
        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=5,
            )
            answer = response.choices[0].message.content.strip().lower()
            return answer.startswith("yes")
        except Exception as e:
            print(f"[RelevanceFilter] LLM check failed, using heuristic: {e}")
            return self._heuristic_relevance_check(query, text)

    def _heuristic_relevance_check(self, query: str, text: str) -> bool:
        """
        Keyword-overlap heuristic. A chunk is relevant if it shares
        at least 2 meaningful terms with the query.
        """
        stopwords = {
            'what', 'are', 'the', 'is', 'for', 'under', 'in', 'of', 'and',
            'how', 'to', 'a', 'an', 'on', 'with', 'by', 'as', 'do', 'does',
            'from', 'or', 'which', 'who', 'when', 'explain', 'give', 'list',
            'about', 'this', 'that', 'it', 'its', 'be', 'been', 'has', 'have',
        }
        query_terms = set(
            re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower())
        ) - stopwords
        text_lower = text.lower()
        overlap = sum(1 for t in query_terms if t in text_lower)
        return overlap >= 2
