import json
from typing import List, Dict, Any, Optional
import httpx
from groq import Groq
from backend.config import settings
from backend.retrieval.relevance_filter import PostRetrievalRelevanceFilter

class GroundedGenerator:
    """
    Assembles prompt context from retrieved chunks and generates factual,
    strictly cited answers using Groq (Llama 3.1 8B) or Ollama.
    """

    def __init__(self):
        self._groq_client = None
        self._relevance_filter: Optional[PostRetrievalRelevanceFilter] = None

    @property
    def groq_client(self) -> Optional[Groq]:
        if self._groq_client is None and settings.groq_api_key:
            try:
                self._groq_client = Groq(api_key=settings.groq_api_key)
            except Exception:
                self._groq_client = None
        return self._groq_client

    @property
    def relevance_filter(self) -> PostRetrievalRelevanceFilter:
        if self._relevance_filter is None:
            self._relevance_filter = PostRetrievalRelevanceFilter(
                groq_client=self.groq_client,
                groq_model=settings.groq_model
            )
        return self._relevance_filter

    def generate_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        subgraph: Optional[Dict[str, Any]] = None,
        retrieval_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Generates an answer grounded strictly in the provided chunks.
        """
        if not retrieved_chunks:
            return {
                "answer": "No relevant regulatory provisions or circulars were found in the indexed corpus to answer this query. Please ensure circulars covering this topic are uploaded.",
                "citations": [],
                "source_chunk_ids": [],
                "subgraph": subgraph or {},
                "retrieval_mode": retrieval_mode
            }

        # Post-retrieval relevance filter — drop noise chunks before context assembly
        retrieved_chunks = self.relevance_filter.filter_chunks(query, retrieved_chunks)

        # Format context chunks
        context_blocks = []
        citations = []
        source_chunk_ids = []

        for idx, chunk in enumerate(retrieved_chunks):
            c_id = chunk["chunk_id"]
            doc_name = chunk.get("document_name", "Unknown")
            code = chunk.get("circular_code", doc_name)
            page = chunk.get("page_number", 1)
            regulator = chunk.get("regulator", "SEBI/RBI")
            text = chunk.get("text", "").strip()

            source_chunk_ids.append(c_id)
            citation_item = {
                "chunk_id": c_id,
                "document_name": doc_name,
                "circular_code": code,
                "regulator": regulator,
                "page_number": page,
                "excerpt": text[:200] + "..." if len(text) > 200 else text,
                "score": chunk.get("rerank_score", chunk.get("score", 0.0))
            }
            citations.append(citation_item)

            context_blocks.append(
                f"[Source {idx+1}] Document: {code} | Page: {page} | Regulator: {regulator}\n{text}"
            )

        context_str = "\n\n---\n\n".join(context_blocks)

        system_instruction = (
            "You are an expert SEBI & RBI regulatory compliance intelligence assistant. "
            "Your task is to provide accurate, comprehensive, and legally sound answers to queries based SOLELY on the provided regulatory circular context. "
            "Rules:\n"
            "1. Ground every claim in the provided context.\n"
            "2. Cite the source circular code and page number when stating requirements (e.g. '[SEBI/HO/... p.2]').\n"
            "3. If different circulars amend, supersede, or modify previous directions, explicitly highlight that chronological progression.\n"
            "4. Never hallucinate provisions not mentioned in the context."
        )

        user_prompt = f"""Context from regulatory documents:
\"\"\"
{context_str}
\"\"\"

User Query: {query}

Please provide a structured, well-explained answer with citations to the specific circulars and pages:"""

        answer_text = ""
        # 1. Try Groq
        if settings.llm_backend == "groq" and self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1024
                )
                answer_text = response.choices[0].message.content
            except Exception as e:
                print(f"Groq generation error: {e}")

        # 2. Try Ollama
        if not answer_text and settings.llm_backend == "ollama":
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(
                        f"{settings.ollama_base_url}/api/chat",
                        json={
                            "model": settings.ollama_model,
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": user_prompt}
                            ],
                            "stream": False,
                            "options": {"temperature": 0.1}
                        }
                    )
                    resp.raise_for_status()
                    answer_text = resp.json()["message"]["content"]
            except Exception as e:
                print(f"Ollama generation error: {e}")

        # 3. Fallback deterministic generator if no API is reachable
        if not answer_text:
            answer_text = self._fallback_answer_synthesis(query, retrieved_chunks)

        return {
            "answer": answer_text,
            "citations": citations,
            "source_chunk_ids": source_chunk_ids,
            "subgraph": subgraph or {},
            "retrieval_mode": retrieval_mode
        }

    def _fallback_answer_synthesis(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Synthesizes an intelligent, structured regulatory compliance answer
        grounded directly in retrieved circular provisions.
        """
        import re

        query_lower = query.lower()
        stopwords = {
            'what', 'are', 'the', 'is', 'for', 'under', 'in', 'of', 'and', 'how',
            'to', 'a', 'an', 'on', 'with', 'by', 'as', 'do', 'does', 'from', 'or',
            'which', 'who', 'when', 'explain', 'give', 'list', 'about'
        }
        query_terms = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', query_lower)) - stopwords

        # 1. Identify primary circular and metadata
        primary_chunk = chunks[0]
        primary_code = primary_chunk.get("circular_code", primary_chunk.get("document_name", "Regulatory Circular"))
        primary_date = primary_chunk.get("circular_date", "")
        primary_regulator = "RBI" if "RBI" in primary_code.upper() else ("SEBI" if "SEBI" in primary_code.upper() else primary_chunk.get("regulator", "SEBI/RBI"))
        primary_page = primary_chunk.get("page_number", 1)

        # 2. Extract and score distinct provisions across chunks
        extracted_provisions = []
        seen_clauses = set()

        for c in chunks:
            c_code = c.get("circular_code", c.get("document_name", "Circular"))
            c_page = c.get("page_number", 1)
            raw_text = c.get("text", "")

            # Reconstruct lines into logical clauses/sentences
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            clauses = []
            curr = []
            for l in lines:
                # If line starts with a list marker like (a), 1., -, etc., start new clause
                if re.match(r'^(?:\([a-zA-Z0-9]+\)|\d+[\.\)]|\-|\*)\s+', l):
                    if curr:
                        clauses.append(' '.join(curr))
                        curr = []
                curr.append(l)
            if curr:
                clauses.append(' '.join(curr))

            for cand in clauses:
                if len(cand) < 20:
                    continue
                # Skip document header lines
                if cand.lower().startswith(('circular ref:', 'date:', 'to all mutual funds', 'madam / dear sir', 'master direction -')):
                    continue

                cand_lower = cand.lower()
                cand_words = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', cand_lower))

                overlap = len(cand_words & query_terms)
                score = overlap * 3.0

                # High-value regulatory indicators
                if re.search(r'\b\d+(\.\d+)?%\b', cand):
                    score += 4.0
                if re.search(r'\b(minimum|maximum|mandatory|mandated|shall|prohibited|target|must|limit|tier|cap|allocat|prescrib|obligat|designated|segregated|hedging)\b', cand_lower):
                    score += 3.0
                if re.search(r'\b(crore|lakh|months?|days?|years?|anbc|ceobe|nav|cut-off|crar|ter|salary|portfolio)\b', cand_lower):
                    score += 2.0

                # Fingerprint to avoid duplicates
                fp = re.sub(r'[^a-zA-Z0-9]', '', cand[:45].lower())
                if fp not in seen_clauses and score > 2.0:
                    seen_clauses.add(fp)
                    extracted_provisions.append({
                        "score": score,
                        "text": cand,
                        "code": c_code,
                        "page": c_page
                    })

        extracted_provisions.sort(key=lambda x: x["score"], reverse=True)
        top_provisions = extracted_provisions[:5]

        # 3. Build structured synthesis response
        header_date_str = f" dated {primary_date}" if primary_date and primary_date != "Unknown" else ""
        lines = [
            f"### Regulatory Determination",
            f"Under **{primary_code}**{header_date_str} (Page {primary_page}), issued by **{primary_regulator}**, the applicable regulatory requirements are established as follows:\n",
            f"### Key Prescribed Provisions & Mandates:"
        ]

        if top_provisions:
            for p in top_provisions:
                cleaned = p['text'].strip()
                # Clean watermark footer if present
                cleaned = re.sub(r'\s*(?:[A-Za-z0-9_\-\.\/]+\s+)?-\s+Regulatory Compliance Intelligence System', '', cleaned)
                # Clean leading list markers
                cleaned = re.sub(r'^(?:\([a-zA-Z0-9]+\)|[0-9]+\.|\-)\s*', '', cleaned)
                # Bold key percentages or statutory limits if present
                formatted = re.sub(r'(\b\d+(\.\d+)?%\b)', r'**\1**', cleaned)
                lines.append(f"- {formatted} `[{p['code']}, p.{p['page']}]`")
        else:
            lines.append(f"> \"{primary_chunk.get('text', '').strip()[:400]}...\" `[{primary_code}, p.{primary_page}]`")

        # 4. Multi-Circular Cross-Reference Grounding (if multiple sources exist)
        other_circulars = {}
        for c in chunks:
            c_code = c.get("circular_code", c.get("document_name"))
            if c_code and c_code != primary_code and c_code not in other_circulars:
                other_circulars[c_code] = c.get("page_number", 1)

        if other_circulars:
            lines.append("\n### Related Regulatory Traversal:")
            for code, page in other_circulars.items():
                lines.append(f"- Connected via regulatory framework: **{code}** (Page {page})")

        return "\n".join(lines)
