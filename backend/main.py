from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes_ingest import router as ingest_router
from backend.api.routes_query import router as query_router
from backend.api.routes_graph import router as graph_router
from backend.evaluation.evaluator import RegulatoryEvaluator
from backend.retrieval.vector_retriever import VectorRetriever
from backend.retrieval.hybrid_merger import HybridMerger
from backend.retrieval.graph_retriever import GraphRetriever
from backend.generation.generator import GroundedGenerator
from backend.ingestion.embedder import ChromaEmbedder
from backend.graph.graph_store import GraphStore

app = FastAPI(
    title="GraphRAG — SEBI/RBI Regulatory Intelligence System",
    description="Knowledge Graph Augmented Generation over SEBI and RBI regulatory circulars",
    version="1.0.0"
)

# Enable CORS for local React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(graph_router)

@app.get("/ping")
def ping():
    """Health check endpoint as requested in Step 1."""
    return {"status": "ok", "system": "GraphRAG Regulatory Intelligence", "version": "1.0.0"}

@app.post("/api/evaluation/benchmark")
def run_evaluation_benchmark(limit: int = 10):
    """
    Executes benchmark comparison between Vanilla RAG and GraphRAG on regulatory questions.
    Returns faithfulness, relevance, and correctness scores broken down by question type.
    """
    embedder = ChromaEmbedder()
    graph_store = GraphStore()
    graph = graph_store.load_graph()

    vector_retriever = VectorRetriever(embedder=embedder)
    graph_retriever = GraphRetriever(graph=graph, chroma_collection=embedder.collection)
    hybrid_merger = HybridMerger(vector_retriever=vector_retriever, graph_retriever=graph_retriever)
    generator = GroundedGenerator()
    evaluator = RegulatoryEvaluator()

    return evaluator.run_comparative_benchmark(
        vector_retriever=vector_retriever,
        hybrid_merger=hybrid_merger,
        generator=generator,
        limit=limit
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
