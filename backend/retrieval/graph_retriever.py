from typing import List, Dict, Any, Set, Tuple
import networkx as nx
import chromadb
from backend.graph.entity_extractor import EntityExtractor
from backend.config import settings

class GraphRetriever:
    """
    Traversal-based retriever that identifies seed entities in the query,
    executes multi-hop BFS traversal (up to depth 2) over the NetworkX knowledge graph,
    and maps the traversed subgraphs back to grounding source chunks.
    """

    def __init__(self, graph: nx.DiGraph, chroma_collection):
        self.graph = graph
        self.chroma_collection = chroma_collection
        self.extractor = EntityExtractor()

    def update_graph(self, graph: nx.DiGraph):
        self.graph = graph

    def extract_seed_entities(self, query: str) -> List[str]:
        """Extracts seed entity IDs from the query text."""
        seed_nodes = []
        # 1. Check spaCy named entities
        spacy_ents = self.extractor.extract_spacy_entities(query)
        for ent in spacy_ents:
            norm_id = EntityExtractor.normalize_id(ent["name"])
            if self.graph.has_node(norm_id) and norm_id not in seed_nodes:
                seed_nodes.append(norm_id)

        # 2. Check token n-grams and aliases against graph nodes
        query_words = [w.strip(",.?!():;") for w in query.lower().split() if len(w) > 2]
        for node_id in self.graph.nodes:
            node_name = self.graph.nodes[node_id].get("name", "").lower()
            if node_id in query.lower() or (node_name and node_name in query.lower()):
                if node_id not in seed_nodes:
                    seed_nodes.append(node_id)

        # 3. Check specific keywords (sebi, rbi, amc, etc.)
        for token in query_words:
            norm_token = EntityExtractor.normalize_id(token)
            if self.graph.has_node(norm_token) and norm_token not in seed_nodes:
                seed_nodes.append(norm_token)

        return seed_nodes

    def traverse_subgraph(self, seed_nodes: List[str], max_depth: int = 2) -> Tuple[Set[str], List[Dict[str, Any]]]:
        """
        Runs BFS traversal from seed nodes up to max_depth.
        Returns the set of visited node IDs and edge list.
        """
        visited_nodes: Set[str] = set()
        subgraph_edges: List[Dict[str, Any]] = []

        for seed in seed_nodes:
            if not self.graph.has_node(seed):
                continue
            visited_nodes.add(seed)

            # BFS up to max_depth
            queue = [(seed, 0)]
            seen_in_seed = {seed}

            while queue:
                current_node, depth = queue.pop(0)
                if depth >= max_depth:
                    continue

                # Explore outgoing and incoming edges
                neighbors = list(self.graph.successors(current_node)) + list(self.graph.predecessors(current_node))
                for neighbor in neighbors:
                    edge_data = self.graph.get_edge_data(current_node, neighbor) or self.graph.get_edge_data(neighbor, current_node) or {}
                    rel_type = edge_data.get("relation_type", "RELATED_TO")
                    
                    subgraph_edges.append({
                        "source": current_node,
                        "target": neighbor,
                        "relation_type": rel_type,
                        "description": edge_data.get("description", "")
                    })

                    if neighbor not in seen_in_seed:
                        seen_in_seed.add(neighbor)
                        visited_nodes.add(neighbor)
                        queue.append((neighbor, depth + 1))

        return visited_nodes, subgraph_edges

    def retrieve(self, query: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Executes graph-guided retrieval:
        1. Identifies seeds in query
        2. Traverses BFS subgraph
        3. Maps traversed nodes & edges to source chunk IDs
        4. Fetches chunk content from ChromaDB
        """
        seed_nodes = self.extract_seed_entities(query)
        visited_nodes, edges = self.traverse_subgraph(seed_nodes, max_depth=max_depth)

        # Collect chunk IDs associated with all visited nodes
        candidate_chunk_ids: Set[str] = set()
        node_details: List[Dict[str, Any]] = []

        for node_id in visited_nodes:
            node_data = self.graph.nodes.get(node_id, {})
            node_details.append({
                "id": node_id,
                "name": node_data.get("name", node_id),
                "type": node_data.get("entity_type", "Entity"),
                "is_seed": node_id in seed_nodes
            })
            for c_id in node_data.get("chunk_ids", []):
                candidate_chunk_ids.add(c_id)

        # Retrieve text for candidate chunks from ChromaDB
        retrieved_chunks: List[Dict[str, Any]] = []
        if candidate_chunk_ids and self.chroma_collection:
            try:
                chroma_res = self.chroma_collection.get(
                    ids=list(candidate_chunk_ids)[:15],
                    include=["documents", "metadatas"]
                )
                for idx, c_id in enumerate(chroma_res.get("ids", [])):
                    meta = chroma_res["metadatas"][idx] if chroma_res.get("metadatas") else {}
                    doc_text = chroma_res["documents"][idx] if chroma_res.get("documents") else ""
                    retrieved_chunks.append({
                        "chunk_id": c_id,
                        "text": doc_text,
                        "document_name": meta.get("document_name", "Unknown"),
                        "circular_code": meta.get("circular_code", "Unknown"),
                        "circular_date": meta.get("circular_date", "Unknown"),
                        "page_number": meta.get("page_number", 1),
                        "score": 0.85,  # graph traversal confidence
                        "retrieval_source": "graph"
                    })
            except Exception as e:
                print(f"Error fetching chunks for graph nodes: {e}")

        # Subgraph JSON for UI highlighting
        subgraph = {
            "seed_nodes": seed_nodes,
            "nodes": node_details,
            "edges": edges,
            "total_nodes": len(visited_nodes),
            "total_edges": len(edges)
        }

        return {
            "chunks": retrieved_chunks,
            "subgraph": subgraph,
            "seed_entities": seed_nodes
        }
