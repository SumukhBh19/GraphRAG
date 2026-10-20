from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.graph.graph_store import GraphStore

router = APIRouter(prefix="/api/graph", tags=["Graph"])
graph_store = GraphStore()

@router.get("")
def get_graph():
    """Returns the full knowledge graph formatted for React Force Graph 2D."""
    graph = graph_store.load_graph()
    return graph_store.get_frontend_payload(graph)

@router.get("/stats")
def get_graph_stats():
    """Returns overview statistics of nodes, relations, and density."""
    graph = graph_store.load_graph()
    payload = graph_store.get_frontend_payload(graph)
    
    type_counts = {}
    for n in payload["nodes"]:
        t = n.get("type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    rel_counts = {}
    for l in payload["links"]:
        t = l.get("type", "Unknown")
        rel_counts[t] = rel_counts.get(t, 0) + 1

    return {
        "nodes_count": len(payload["nodes"]),
        "links_count": len(payload["links"]),
        "node_types": type_counts,
        "relation_types": rel_counts
    }

@router.get("/search")
def search_graph(q: str = Query(..., min_length=1)):
    """Searches for nodes matching the query string."""
    graph = graph_store.load_graph()
    query_lower = q.lower().strip()
    matches = []

    for node_id, data in graph.nodes(data=True):
        name = data.get("name", node_id)
        if query_lower in node_id.lower() or query_lower in name.lower():
            matches.append({
                "id": node_id,
                "name": name,
                "type": data.get("entity_type", "Entity"),
                "source_documents": data.get("source_documents", []),
                "chunk_ids": data.get("chunk_ids", [])
            })

    return {"query": q, "count": len(matches), "results": matches}

@router.get("/node/{node_id}")
def get_node_details(node_id: str):
    """Fetches details for a specific node and its immediate 1-hop neighborhood."""
    graph = graph_store.load_graph()
    if not graph.has_node(node_id):
        raise HTTPException(status_code=404, detail="Node not found in graph")

    node_data = graph.nodes[node_id]
    neighbors = []
    
    for succ in graph.successors(node_id):
        edge = graph.get_edge_data(node_id, succ)
        neighbors.append({
            "target_id": succ,
            "target_name": graph.nodes[succ].get("name", succ),
            "target_type": graph.nodes[succ].get("entity_type", "Entity"),
            "relation": edge.get("relation_type", "RELATED_TO"),
            "direction": "outgoing"
        })

    for pred in graph.predecessors(node_id):
        edge = graph.get_edge_data(pred, node_id)
        neighbors.append({
            "target_id": pred,
            "target_name": graph.nodes[pred].get("name", pred),
            "target_type": graph.nodes[pred].get("entity_type", "Entity"),
            "relation": edge.get("relation_type", "RELATED_TO"),
            "direction": "incoming"
        })

    return {
        "id": node_id,
        "name": node_data.get("name", node_id),
        "type": node_data.get("entity_type", "Entity"),
        "source_documents": node_data.get("source_documents", []),
        "pages": node_data.get("pages", []),
        "chunk_ids": node_data.get("chunk_ids", []),
        "properties": node_data.get("properties", {}),
        "neighbors": neighbors
    }
