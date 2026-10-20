import pytest
import networkx as nx
from backend.graph.entity_extractor import EntityExtractor, ExtractedEntity, ExtractedRelationship, ExtractionResult
from backend.graph.graph_builder import KnowledgeGraphBuilder
from backend.graph.graph_store import GraphStore

def test_normalization():
    assert EntityExtractor.normalize_id("SEBI") == "sebi"
    assert EntityExtractor.normalize_id("S.E.B.I.") == "sebi"
    assert EntityExtractor.normalize_id("Reserve Bank of India") == "reserve_bank_of_india"
    assert EntityExtractor.normalize_id("Asset Management Company") == "asset_management_company"

def test_graph_construction_and_traversal():
    builder = KnowledgeGraphBuilder()
    
    # Simulate extraction result for circular 1
    ext1 = ExtractionResult(
        entities=[
            ExtractedEntity(id="sebi_mf_2020_172", name="SEBI/HO/IMD/DF3/CIR/P/2020/172", type="Circular"),
            ExtractedEntity(id="sebi", name="SEBI", type="Entity"),
            ExtractedEntity(id="multi_cap_fund", name="Multi Cap Fund", type="Instrument"),
            ExtractedEntity(id="large_cap", name="Large Cap Companies", type="Instrument")
        ],
        relationships=[
            ExtractedRelationship(source="sebi_mf_2020_172", target="sebi", type="ISSUED_BY"),
            ExtractedRelationship(source="sebi_mf_2020_172", target="multi_cap_fund", type="GOVERNS"),
            ExtractedRelationship(source="multi_cap_fund", target="large_cap", type="MANDATES")
        ]
    )

    builder.add_extraction_result(ext1, "SEBI_MF_2020_172.pdf", 1, "chunk_1")

    assert builder.graph.has_node("sebi")
    assert builder.graph.has_node("multi_cap_fund")
    assert builder.graph.has_edge("sebi_mf_2020_172", "multi_cap_fund")

    # Verify 2-hop BFS reachability from circular
    # Hop 1: sebi, multi_cap_fund
    # Hop 2: large_cap
    neighbors_1 = set(builder.graph.successors("sebi_mf_2020_172"))
    assert "multi_cap_fund" in neighbors_1
    assert "sebi" in neighbors_1

    neighbors_2 = set(builder.graph.successors("multi_cap_fund"))
    assert "large_cap" in neighbors_2

def test_graph_store_node_link_export(tmp_path):
    builder = KnowledgeGraphBuilder()
    ext = ExtractionResult(
        entities=[
            ExtractedEntity(id="rbi", name="Reserve Bank of India", type="Entity"),
            ExtractedEntity(id="psl", name="Priority Sector Lending", type="Obligation")
        ],
        relationships=[
            ExtractedRelationship(source="rbi", target="psl", type="GOVERNS")
        ]
    )
    builder.add_extraction_result(ext, "RBI_FIDD_2020_008.pdf", 1, "chunk_rbi_1")

    store = GraphStore(storage_path=tmp_path / "test_graph.json")
    saved_path = store.save_graph(builder.graph)
    assert saved_path.exists()

    payload = store.get_frontend_payload(builder.graph)
    assert "nodes" in payload
    assert "links" in payload
    assert len(payload["nodes"]) == 2
    assert len(payload["links"]) == 1
    assert payload["nodes"][0]["color"] is not None
