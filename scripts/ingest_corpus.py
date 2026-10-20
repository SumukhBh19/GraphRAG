"""
Batch ingestion script: parses all PDFs in data/raw/, generates chunks,
computes vector embeddings, extracts entities & relationships,
and constructs the persisted NetworkX knowledge graph.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.ingestion.pdf_parser import PDFParser
from backend.ingestion.chunker import RegulatoryChunker
from backend.ingestion.embedder import ChromaEmbedder
from backend.graph.entity_extractor import EntityExtractor
from backend.graph.graph_builder import KnowledgeGraphBuilder
from backend.graph.graph_store import GraphStore

def main():
    print("=== Starting Ingestion Pipeline ===")
    pdf_parser = PDFParser()
    chunker = RegulatoryChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        sebi_chunk_size=settings.sebi_chunk_size,
        sebi_chunk_overlap=settings.sebi_chunk_overlap
    )
    embedder = ChromaEmbedder()
    try:
        embedder._client.delete_collection("sebi_rbi_regulatory_chunks")
    except Exception:
        pass
    embedder.collection = embedder._client.get_or_create_collection(
        name="sebi_rbi_regulatory_chunks",
        metadata={"hnsw:space": "cosine"}
    )
    graph_store = GraphStore()
    import networkx as nx
    graph_builder = KnowledgeGraphBuilder(graph=nx.DiGraph())
    extractor = EntityExtractor()

    pdf_files = list(settings.data_raw_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files in {settings.data_raw_dir}")

    total_chunks = 0
    total_nodes = 0
    total_edges = 0

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        # 1. Parse PDF
        parsed = pdf_parser.parse_pdf(pdf_path)
        print(f"  Pages: {parsed['total_pages']}, Code: {parsed['circular_code']}, Date: {parsed['circular_date']}")

        # 2. Chunk text
        chunks = chunker.chunk_document(parsed)
        print(f"  Generated {len(chunks)} chunks")
        total_chunks += len(chunks)

        # 3. Add to ChromaDB
        embedder.add_chunks(chunks)

        # 4. Extract entities & relations
        for chunk in chunks:
            ext_res = extractor.extract_from_chunk(chunk)
            graph_builder.add_extraction_result(
                extraction=ext_res,
                document_name=pdf_path.name,
                page_number=chunk["page_number"],
                chunk_id=chunk["chunk_id"]
            )
            total_nodes += len(ext_res.entities)
            total_edges += len(ext_res.relationships)

    # 5. Persist graph
    saved_path = graph_store.save_graph(graph_builder.graph)
    stats = graph_builder.get_stats()

    print("\n=== Ingestion Pipeline Completed Successfully ===")
    print(f"Persisted Graph: {saved_path}")
    print(f"Total Chunks: {total_chunks}")
    print(f"Unique Graph Nodes: {stats['total_nodes']}")
    print(f"Unique Graph Edges: {stats['total_edges']}")
    print(f"Node Types Breakdown: {stats['node_types']}")
    print(f"Relation Types Breakdown: {stats['relation_types']}")

if __name__ == "__main__":
    main()
