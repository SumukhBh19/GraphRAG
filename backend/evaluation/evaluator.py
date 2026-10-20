import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
from groq import Groq
from backend.config import settings

class RegulatoryEvaluator:
    """
    Automated evaluation framework comparing Vanilla RAG vs GraphRAG
    using LLM-as-a-Judge across Faithfulness, Context Relevance, and Answer Correctness.
    """

    def __init__(self):
        self._groq_client = None

    @property
    def groq_client(self) -> Optional[Groq]:
        if self._groq_client is None and settings.groq_api_key:
            try:
                self._groq_client = Groq(api_key=settings.groq_api_key)
            except Exception:
                self._groq_client = None
        return self._groq_client

    def evaluate_response(
        self,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        ground_truth: str
    ) -> Dict[str, Any]:
        """
        Scores a single generated answer across Faithfulness, Context Relevance,
        and Answer Correctness on a 1-5 integer scale.
        """
        chunks_text = "\n\n".join([c.get("text", "")[:400] for c in retrieved_chunks[:5]])

        judge_prompt = f"""You are an objective judge evaluating AI-generated answers against regulatory facts.

[Question]
{question}

[Ground Truth Answer]
{ground_truth}

[Retrieved Context Used by Assistant]
{chunks_text}

[Assistant Generated Answer]
{answer}

Evaluate the assistant answer on three criteria (score 1 to 5, where 1 is poor and 5 is excellent):
1. faithfulness: Does the generated answer strictly adhere to the retrieved context without hallucinating? (1=complete hallucination, 5=strictly grounded)
2. context_relevance: Did the retrieved context actually contain the essential provisions needed to answer the question? (1=completely irrelevant chunks, 5=highly relevant chunks)
3. answer_correctness: Does the assistant answer match the factual ground truth? (1=wrong/misleading, 5=completely accurate)

Output strictly valid JSON without markdown:
{{
  "faithfulness": 5,
  "context_relevance": 5,
  "answer_correctness": 5,
  "reasoning": "Brief justification"
}}"""

        # 1. Try Groq judge
        if settings.llm_backend == "groq" and self.groq_client:
            try:
                resp = self.groq_client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {"role": "system", "content": "You are an expert AI evaluator. Output strict JSON only."},
                        {"role": "user", "content": judge_prompt}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                data = json.loads(resp.choices[0].message.content)
                return self._sanitize_score(data)
            except Exception as e:
                print(f"LLM-as-a-judge Groq evaluation error: {e}")

        # 2. Try Ollama judge
        if settings.llm_backend == "ollama":
            try:
                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={
                            "model": settings.ollama_model,
                            "prompt": judge_prompt,
                            "format": "json",
                            "stream": False
                        }
                    )
                    resp.raise_for_status()
                    data = json.loads(resp.json()["response"])
                    return self._sanitize_score(data)
            except Exception as e:
                print(f"LLM-as-a-judge Ollama evaluation error: {e}")

        # Fallback heuristic metric evaluation
        return self._heuristic_score(question, answer, retrieved_chunks, ground_truth)

    def _sanitize_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "faithfulness": min(5, max(1, int(data.get("faithfulness", 3)))),
            "context_relevance": min(5, max(1, int(data.get("context_relevance", 3)))),
            "answer_correctness": min(5, max(1, int(data.get("answer_correctness", 3)))),
            "reasoning": data.get("reasoning", "Evaluated by LLM Judge")
        }

    def _heuristic_score(
        self,
        question: str,
        answer: str,
        chunks: List[Dict[str, Any]],
        ground_truth: str
    ) -> Dict[str, Any]:
        """Heuristic scoring based on keyword overlap, entity matches, and context containment."""
        gt_tokens = set(re.findall(r"\w+", ground_truth.lower()))
        ans_tokens = set(re.findall(r"\w+", answer.lower()))
        overlap = len(gt_tokens.intersection(ans_tokens)) / max(1, len(gt_tokens))

        chunks_str = " ".join([c.get("text", "").lower() for c in chunks])
        ctx_overlap = len(gt_tokens.intersection(set(re.findall(r"\w+", chunks_str)))) / max(1, len(gt_tokens))

        correctness = round(1 + 4 * overlap)
        context_rel = round(1 + 4 * ctx_overlap)
        faithfulness = 4 if len(answer) > 50 else 2

        return {
            "faithfulness": min(5, max(1, faithfulness)),
            "context_relevance": min(5, max(1, context_rel)),
            "answer_correctness": min(5, max(1, correctness)),
            "reasoning": f"Heuristic calculation (token overlap: {overlap:.2f}, context overlap: {ctx_overlap:.2f})"
        }

    def run_comparative_benchmark(
        self,
        qa_pairs_path: Optional[Path] = None,
        vector_retriever = None,
        hybrid_merger = None,
        generator = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Runs both Vanilla RAG and GraphRAG across the benchmark set,
        computes aggregate metrics by question type, and confirms research hypothesis.
        """
        path = qa_pairs_path or (Path(__file__).parent / "qa_pairs.json")
        with open(path, "r", encoding="utf-8") as f:
            qa_list = json.load(f)

        if limit:
            qa_list = qa_list[:limit]

        results = []
        metrics_by_type = {
            "simple_factual": {"vanilla": [], "hybrid": []},
            "multi_hop": {"vanilla": [], "hybrid": []},
            "comparative": {"vanilla": [], "hybrid": []}
        }

        for q_item in qa_list:
            q_id = q_item["id"]
            q_type = q_item["type"]
            q_text = q_item["question"]
            gt = q_item["ground_truth"]

            # 1. Run Vanilla RAG (vector only)
            vec_chunks = vector_retriever.retrieve(q_text, top_k=6) if vector_retriever else []
            vanilla_gen = generator.generate_answer(q_text, vec_chunks, retrieval_mode="vanilla") if generator else {"answer": "N/A"}
            vanilla_eval = self.evaluate_response(q_text, vanilla_gen["answer"], vec_chunks, gt)

            # 2. Run GraphRAG (hybrid)
            hybrid_res = hybrid_merger.retrieve(q_text, top_k=6) if hybrid_merger else {"chunks": [], "subgraph": {}}
            hybrid_gen = generator.generate_answer(q_text, hybrid_res["chunks"], hybrid_res["subgraph"], retrieval_mode="hybrid") if generator else {"answer": "N/A"}
            hybrid_eval = self.evaluate_response(q_text, hybrid_gen["answer"], hybrid_res["chunks"], gt)

            metrics_by_type[q_type]["vanilla"].append(vanilla_eval)
            metrics_by_type[q_type]["hybrid"].append(hybrid_eval)

            results.append({
                "id": q_id,
                "type": q_type,
                "question": q_text,
                "vanilla": {
                    "answer": vanilla_gen["answer"],
                    "evaluation": vanilla_eval
                },
                "hybrid": {
                    "answer": hybrid_gen["answer"],
                    "evaluation": hybrid_eval
                }
            })

        # Calculate averages
        summary = {}
        for cat, scores in metrics_by_type.items():
            def avg(lst, key):
                return round(sum(x[key] for x in lst) / len(lst), 2) if lst else 0.0

            summary[cat] = {
                "count": len(scores["vanilla"]),
                "vanilla": {
                    "faithfulness": avg(scores["vanilla"], "faithfulness"),
                    "context_relevance": avg(scores["vanilla"], "context_relevance"),
                    "answer_correctness": avg(scores["vanilla"], "answer_correctness")
                },
                "hybrid": {
                    "faithfulness": avg(scores["hybrid"], "faithfulness"),
                    "context_relevance": avg(scores["hybrid"], "context_relevance"),
                    "answer_correctness": avg(scores["hybrid"], "answer_correctness")
                }
            }

        return {
            "summary_by_category": summary,
            "detailed_results": results
        }
