import json
from pathlib import Path
from typing import Dict, Any, Optional
import networkx as nx
from backend.config import settings

class GraphStore:
    """
    Handles serialization and persistence of the NetworkX knowledge graph
    in standard node-link JSON format compatible with react-force-graph-2d.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (settings.data_graphs_dir / "knowledge_graph.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save_graph(self, graph: nx.DiGraph) -> Path:
        """Serializes the graph to JSON in node-link format."""
        data = nx.node_link_data(graph)
        edges = data.get("links") or data.get("edges", [])

        payload = {
            "metadata": {
                "total_nodes": graph.number_of_nodes(),
                "total_edges": graph.number_of_edges(),
            },
            "nodes": data.get("nodes", []),
            "links": edges,
            "edges": edges,
            "directed": True,
            "multigraph": False,
            "graph": {}
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return self.storage_path

    def load_graph(self) -> nx.DiGraph:
        """Loads the graph from disk, or initializes an empty DiGraph if absent."""
        if not self.storage_path.exists():
            return nx.DiGraph()

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return nx.node_link_graph(data)
        except Exception as e:
            print(f"Error loading graph from {self.storage_path}: {e}")
            return nx.DiGraph()

    def get_frontend_payload(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Formats the graph for direct consumption by React Force Graph."""
        data = nx.node_link_data(graph)
        raw_edges = data.get("links") or data.get("edges", [])

        # Color mapping for frontend visualizer
        color_map = {
            "Regulation": "#3b82f6",    # Blue
            "Circular": "#6366f1",      # Indigo
            "Entity": "#10b981",        # Emerald Green
            "Instrument": "#f59e0b",    # Amber
            "Date": "#94a3b8",          # Slate Gray
            "Section": "#8b5cf6",       # Purple
            "Obligation": "#ef4444"     # Rose Red
        }

        nodes = []
        for n in data.get("nodes", []):
            node_id = n.get("id")
            entity_type = n.get("entity_type", "Entity")
            nodes.append({
                "id": node_id,
                "name": n.get("name", node_id),
                "type": entity_type,
                "color": color_map.get(entity_type, "#06b6d4"),
                "val": min(10, 2 + len(n.get("chunk_ids", []))),
                "source_documents": n.get("source_documents", []),
                "pages": n.get("pages", []),
                "chunk_ids": n.get("chunk_ids", []),
                "properties": n.get("properties", {})
            })

        links = []
        for link in raw_edges:
            links.append({
                "source": link["source"],
                "target": link["target"],
                "type": link.get("relation_type", "REL"),
                "label": link.get("relation_type", "REL"),
                "description": link.get("description", ""),
                "confidence": link.get("confidence", 1.0),
                "chunk_ids": link.get("chunk_ids", [])
            })

        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "nodes_count": len(nodes),
                "links_count": len(links)
            }
        }
