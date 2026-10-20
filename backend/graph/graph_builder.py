from typing import List, Dict, Any, Optional
import networkx as nx
from backend.graph.entity_extractor import ExtractionResult, ExtractedEntity, ExtractedRelationship

class KnowledgeGraphBuilder:
    """
    Constructs and maintains the NetworkX DiGraph representing regulatory entities
    and relationships across all parsed circulars and directions.
    """

    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph: nx.DiGraph = graph if graph is not None else nx.DiGraph()

    def add_extraction_result(
        self,
        extraction: ExtractionResult,
        document_name: str,
        page_number: int,
        chunk_id: str
    ):
        """
        Integrates entities and relationships from a single chunk extraction into the graph.
        Performs node deduplication, attribute merging, and chunk provenance tracking.
        """
        # 1. Add / update nodes
        for entity in extraction.entities:
            node_id = entity.id
            if not self.graph.has_node(node_id):
                self.graph.add_node(
                    node_id,
                    name=entity.name,
                    entity_type=entity.type,
                    source_documents=[document_name],
                    pages=[page_number],
                    chunk_ids=[chunk_id],
                    properties=entity.properties or {}
                )
            else:
                # Merge metadata
                node_data = self.graph.nodes[node_id]
                if document_name not in node_data.get("source_documents", []):
                    node_data["source_documents"].append(document_name)
                if page_number not in node_data.get("pages", []):
                    node_data["pages"].append(page_number)
                if chunk_id not in node_data.get("chunk_ids", []):
                    node_data["chunk_ids"].append(chunk_id)
                # Keep most descriptive name
                if len(entity.name) > len(node_data.get("name", "")):
                    node_data["name"] = entity.name

        # 2. Add / update edges
        for rel in extraction.relationships:
            u, v = rel.source, rel.target
            if u == v:
                continue

            # Ensure nodes exist
            if not self.graph.has_node(u):
                self.graph.add_node(u, name=u.replace("_", " ").title(), entity_type="Entity", source_documents=[document_name], pages=[page_number], chunk_ids=[chunk_id])
            if not self.graph.has_node(v):
                self.graph.add_node(v, name=v.replace("_", " ").title(), entity_type="Entity", source_documents=[document_name], pages=[page_number], chunk_ids=[chunk_id])

            if self.graph.has_edge(u, v):
                edge_data = self.graph[u][v]
                if chunk_id not in edge_data.get("chunk_ids", []):
                    edge_data["chunk_ids"].append(chunk_id)
                if document_name not in edge_data.get("source_documents", []):
                    edge_data["source_documents"].append(document_name)
            else:
                self.graph.add_edge(
                    u,
                    v,
                    relation_type=rel.type,
                    description=rel.description or "",
                    confidence=rel.confidence,
                    source_chunk_id=chunk_id,
                    chunk_ids=[chunk_id],
                    source_documents=[document_name]
                )

    def get_stats(self) -> Dict[str, Any]:
        """Returns graph metrics."""
        type_counts = {}
        for _, d in self.graph.nodes(data=True):
            t = d.get("entity_type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        rel_counts = {}
        for _, _, d in self.graph.edges(data=True):
            r = d.get("relation_type", "Unknown")
            rel_counts[r] = rel_counts.get(r, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": type_counts,
            "relation_types": rel_counts,
            "density": nx.density(self.graph) if self.graph.number_of_nodes() > 1 else 0.0
        }
