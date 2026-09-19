import pytest
from typing import List, Dict, Any, Tuple
from src.retrieval.models import Candidate, CandidateSet
from src.retrieval.representation import RetrievalRepresentationBuilder
from src.retrieval.engine import RetrievalEngine
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.vector_store import VectorStore
from src.retrieval.lexical import LexicalRetriever
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance

# --- Mocks for unit tests ---

class FakeEmbeddingProvider(EmbeddingProvider):
    def get_dimension(self) -> int:
        return 1024
        
    def encode(self, texts: List[str]) -> List[List[float]]:
        # Fake random vectors
        import random
        return [[random.random() for _ in range(1024)] for _ in texts]

class FakeVectorStore(VectorStore):
    def __init__(self):
        self.upserted_records = []
        self.search_results = []
        
    def upsert(self, records: List[Dict[str, Any]]):
        self.upserted_records.extend(records)
        
    def search(self, query_embedding: List[float], top_k: int = 50, exclude_material_id: str = None) -> List[Tuple[str, float]]:
        # Return pre-programmed search results, filtering self match
        return [(mat_id, score) for mat_id, score in self.search_results if mat_id != exclude_material_id][:top_k]
        
    def get_all_materials(self) -> List[Dict[str, Any]]:
        return []

class FakeLexicalRetriever(LexicalRetriever):
    def __init__(self):
        self.search_results = []
        
    def refresh(self, corpus: List[Dict[str, Any]]):
        pass

    def search(self, query_text: str, top_k: int = 50) -> List[Tuple[str, float]]:
        return self.search_results[:top_k]

# --- Tests ---

def get_prov(record_id: str) -> Provenance:
    return Provenance(
        cpse="TEST",
        source_system="ERP",
        source_type="FILE",
        source_record_id=record_id,
        source_file="test.csv",
        source_row=1,
        ingestion_timestamp="2026-09-19T00:00:00Z",
        processing_version="v1"
    )

def test_representation_builder_excludes_manufacturer():
    record = UnifiedMaterialRecord(
        provenance=get_prov("m1"),
        description_original="gate valve test",
        normalized_description="gate valve test",
        commodity_class="VALVE",
        manufacturer="Acme Corp",
        manufacturer_part_number="XYZ-123"
    )
    builder = RetrievalRepresentationBuilder()
    rep = builder.build(record)
    
    assert "gate valve test" in rep
    assert "Commodity Class: VALVE" in rep
    assert "Acme Corp" not in rep
    assert "XYZ-123" not in rep
    assert "manufacturer" not in builder.fields

def test_engine_candidate_union_and_deduplication():
    vstore = FakeVectorStore()
    # Program Vector to return m2, m3
    vstore.search_results = [("m2", 0.95), ("m3", 0.85)]
    
    lexical = FakeLexicalRetriever()
    # Program Lexical to return m2, m4
    lexical.search_results = [("m2", 15.0), ("m4", 10.0)]
    
    engine = RetrievalEngine(
        vector_store=vstore,
        embedding_provider=FakeEmbeddingProvider(),
        lexical_retriever=lexical
    )
    
    query = UnifiedMaterialRecord(
        provenance=get_prov("m1"),
        description_original="query desc",
        normalized_description="query desc"
    )
    
    candidate_set = engine.retrieve_candidates(query, top_k=50)
    
    assert candidate_set.query_material_id == "m1"
    assert len(candidate_set.candidates) == 3 # m2, m3, m4
    
    # Check deduplication on m2
    m2_candidate = next(c for c in candidate_set.candidates if c.material_id == "m2")
    assert "VECTOR" in m2_candidate.retrieval_sources
    assert "BM25" in m2_candidate.retrieval_sources
    assert m2_candidate.vector_similarity == 0.95
    assert m2_candidate.bm25_score == 15.0
    
    # Check m3
    m3_candidate = next(c for c in candidate_set.candidates if c.material_id == "m3")
    assert m3_candidate.retrieval_sources == ["VECTOR"]
    
    # Check m4
    m4_candidate = next(c for c in candidate_set.candidates if c.material_id == "m4")
    assert m4_candidate.retrieval_sources == ["BM25"]

def test_engine_removes_self_match():
    vstore = FakeVectorStore()
    # m1 is self
    vstore.search_results = [("m1", 0.99), ("m2", 0.85)]
    
    lexical = FakeLexicalRetriever()
    lexical.search_results = [("m1", 20.0)]
    
    engine = RetrievalEngine(
        vector_store=vstore,
        embedding_provider=FakeEmbeddingProvider(),
        lexical_retriever=lexical
    )
    
    query = UnifiedMaterialRecord(
        provenance=get_prov("m1"),
        description_original="query desc",
        normalized_description="query desc"
    )
    
    candidate_set = engine.retrieve_candidates(query, top_k=50)
    
    assert len(candidate_set.candidates) == 1
    assert candidate_set.candidates[0].material_id == "m2"
    assert "m1" not in [c.material_id for c in candidate_set.candidates]

def test_engine_enforces_top_k():
    vstore = FakeVectorStore()
    vstore.search_results = [(f"v{i}", 0.9) for i in range(10)]
    
    lexical = FakeLexicalRetriever()
    lexical.search_results = [(f"l{i}", 10.0) for i in range(10)]
    
    engine = RetrievalEngine(
        vector_store=vstore,
        embedding_provider=FakeEmbeddingProvider(),
        lexical_retriever=lexical
    )
    
    query = UnifiedMaterialRecord(
        provenance=get_prov("m1"),
        description_original="query desc",
        normalized_description="query desc"
    )
    
    # We have 20 candidates total. Request top 5.
    candidate_set = engine.retrieve_candidates(query, top_k=5)
    
    assert len(candidate_set.candidates) == 5
