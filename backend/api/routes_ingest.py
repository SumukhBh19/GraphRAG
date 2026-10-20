import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from backend.config import settings
from backend.ingestion.pdf_parser import PDFParser
from backend.ingestion.chunker import RegulatoryChunker
from backend.ingestion.embedder import ChromaEmbedder
from backend.graph.entity_extractor import EntityExtractor
from backend.graph.graph_builder import KnowledgeGraphBuilder
from backend.graph.graph_store import GraphStore

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

# Shared service instances
pdf_parser = PDFParser()
chunker = RegulatoryChunker(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
    sebi_chunk_size=settings.sebi_chunk_size,
    sebi_chunk_overlap=settings.sebi_chunk_overlap
)
embedder = ChromaEmbedder()
graph_store = GraphStore()
graph_builder = KnowledgeGraphBuilder(graph=graph_store.load_graph())
extractor = EntityExtractor()

# Global tracking of processed documents
processed_docs_registry: Dict[str, Dict[str, Any]] = {}

def process_pdf_pipeline(file_path: Path) -> Dict[str, Any]:
    """Runs the full ingestion pipeline: parse -> chunk -> embed -> extract -> graph."""
    doc_id = file_path.name
    processed_docs_registry[doc_id] = {
        "file_name": file_path.name,
        "status": "processing",
        "regulator": "SEBI" if "sebi" in file_path.name.lower() else "RBI",
        "chunks_count": 0,
        "nodes_extracted": 0,
        "edges_extracted": 0
    }

    try:
        # 1. Parse PDF
        parsed = pdf_parser.parse_pdf(file_path)

        # 2. Chunk document
        chunks = chunker.chunk_document(parsed)
        processed_docs_registry[doc_id]["chunks_count"] = len(chunks)

        # 3. Embed and upsert to ChromaDB
        embedder.add_chunks(chunks)

        # 4. Extract entities & update Knowledge Graph
        total_nodes = 0
        total_edges = 0
        for chunk in chunks:
            ext_res = extractor.extract_from_chunk(chunk)
            graph_builder.add_extraction_result(
                extraction=ext_res,
                document_name=parsed["file_name"],
                page_number=chunk["page_number"],
                chunk_id=chunk["chunk_id"]
            )
            total_nodes += len(ext_res.entities)
            total_edges += len(ext_res.relationships)

        # 5. Persist graph
        graph_store.save_graph(graph_builder.graph)

        processed_docs_registry[doc_id].update({
            "status": "ready",
            "circular_code": parsed.get("circular_code", file_path.stem),
            "circular_date": parsed.get("circular_date", "Unknown"),
            "pages": parsed["total_pages"],
            "nodes_extracted": total_nodes,
            "edges_extracted": total_edges
        })
        return processed_docs_registry[doc_id]

    except Exception as e:
        processed_docs_registry[doc_id]["status"] = f"error: {str(e)}"
        raise e

@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """Uploads one or more SEBI/RBI PDF circulars and indexes them."""
    uploaded_info = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")

        save_path = settings.data_raw_dir / file.filename
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run pipeline in background
        background_tasks.add_task(process_pdf_pipeline, save_path)

        uploaded_info.append({
            "filename": file.filename,
            "status": "queued for processing",
            "path": str(save_path)
        })

    return {"uploaded": uploaded_info, "message": "Files queued for parsing, embedding and graph extraction"}

@router.get("/documents")
def list_documents():
    """Returns list of all uploaded and processed regulatory documents."""
    # Check disk for any raw files not yet in registry
    for p in settings.data_raw_dir.glob("*.pdf"):
        if p.name not in processed_docs_registry:
            processed_docs_registry[p.name] = {
                "file_name": p.name,
                "status": "ready" if (settings.data_graphs_dir / "knowledge_graph.json").exists() else "unprocessed",
                "regulator": "SEBI" if "sebi" in p.name.lower() else "RBI",
                "chunks_count": 0,
                "pages": 0
            }

    return {
        "total": len(processed_docs_registry),
        "documents": list(processed_docs_registry.values())
    }
