import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    # LLM Settings
    llm_backend: str = os.getenv("LLM_BACKEND", "groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # Embeddings & Reranking
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    reranker_model_name: str = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    # Directories
    data_raw_dir: Path = BASE_DIR / "data" / "raw"
    data_processed_dir: Path = BASE_DIR / "data" / "processed"
    data_graphs_dir: Path = BASE_DIR / "data" / "graphs"
    chroma_persist_dir: Path = BASE_DIR / "data" / "chroma_db"

    # Graph & Retrieval Config
    graph_retrieval_depth: int = int(os.getenv("GRAPH_RETRIEVAL_DEPTH", "2"))
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "6"))
    chunk_size: int = 900
    chunk_overlap: int = 150
    sebi_chunk_size: int = 2800
    sebi_chunk_overlap: int = 350

settings = Settings()

# Ensure directories exist
settings.data_raw_dir.mkdir(parents=True, exist_ok=True)
settings.data_processed_dir.mkdir(parents=True, exist_ok=True)
settings.data_graphs_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
