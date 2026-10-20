from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.ingestion.embedder import ChromaEmbedder
from backend.retrieval.vector_retriever import VectorRetriever
from backend.retrieval.graph_retriever import GraphRetriever
from backend.retrieval.hybrid_merger import HybridMerger
from backend.generation.generator import GroundedGenerator
from backend.graph.graph_store import GraphStore

router = APIRouter(prefix="/api/query", tags=["Query"])

# Initialize retrieval and generation dependencies
embedder = ChromaEmbedder()
graph_store = GraphStore()
loaded_graph = graph_store.load_graph()

vector_retriever = VectorRetriever(embedder=embedder)
graph_retriever = GraphRetriever(graph=loaded_graph, chroma_collection=embedder.collection)
hybrid_merger = HybridMerger(vector_retriever=vector_retriever, graph_retriever=graph_retriever)
generator = GroundedGenerator()

class QueryRequest(BaseModel):
    query: str = Field(..., description="Regulatory question from user")
    mode: str = Field(default="hybrid", description="'hybrid' for GraphRAG, 'vanilla' for pure vector RAG")
    top_k: int = Field(default=6, description="Number of context chunks to assemble")

@router.post("")
def query_system(req: QueryRequest):
    """
    Executes grounded Q&A over the regulatory corpus.
    Supports GraphRAG (hybrid vector + graph traversal) and Vanilla RAG baseline.
    """
    # Refresh graph in memory in case new documents were ingested
    current_graph = graph_store.load_graph()
    graph_retriever.update_graph(current_graph)

    if req.mode == "vanilla":
        retrieved_chunks = vector_retriever.retrieve(req.query, top_k=req.top_k)
        result = generator.generate_answer(
            query=req.query,
            retrieved_chunks=retrieved_chunks,
            subgraph={"nodes": [], "edges": []},
            retrieval_mode="vanilla"
        )
    else:
        hybrid_res = hybrid_merger.retrieve(req.query, top_k=req.top_k)
        result = generator.generate_answer(
            query=req.query,
            retrieved_chunks=hybrid_res["chunks"],
            subgraph=hybrid_res["subgraph"],
            retrieval_mode="hybrid"
        )

    return result
