from typing import List
from src.retrieval.models import Candidate, CandidateSet
from src.retrieval.lexical import LexicalRetriever
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.vector_store import VectorStore
from src.retrieval.representation import RetrievalRepresentationBuilder
from src.ingestion.unified_schema import UnifiedMaterialRecord

class RetrievalEngine:
    def __init__(
        self, 
        vector_store: VectorStore, 
        embedding_provider: EmbeddingProvider, 
        lexical_retriever: LexicalRetriever,
        retrieval_version: str = "lane5-v1"
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.lexical_retriever = lexical_retriever
        self.representation_builder = RetrievalRepresentationBuilder()
        self.retrieval_version = retrieval_version
        
    def retrieve_candidates(self, query_record: UnifiedMaterialRecord, top_k: int = 50) -> CandidateSet:
        # 1. Build Query Representation
        query_text = self.representation_builder.build(query_record)
        query_id = query_record.provenance.source_record_id # Using source_record_id as material_id
        
        # 2. Get Vector Candidates
        vector_candidates = []
        if query_text:
            query_embedding = self.embedding_provider.encode([query_text])[0]
            vector_results = self.vector_store.search(
                query_embedding=query_embedding, 
                top_k=top_k, 
                exclude_material_id=query_id
            )
            for mat_id, score in vector_results:
                vector_candidates.append({
                    "material_id": mat_id,
                    "vector_similarity": score
                })
                
        # Track metrics
        self_matches_removed = 0
        
        # 3. Get Lexical Candidates
        lexical_candidates = []
        if query_text:
            lexical_results = self.lexical_retriever.search(query_text, top_k=top_k)
            for mat_id, score in lexical_results:
                if mat_id != query_id:  # Exclude self-match
                    lexical_candidates.append({
                        "material_id": mat_id,
                        "bm25_score": score
                    })
                else:
                    self_matches_removed += 1
                    
        # Add vector self match tracking
        vector_candidates_clean = []
        for vc in vector_candidates:
            if vc["material_id"] != query_id:
                vector_candidates_clean.append(vc)
            else:
                self_matches_removed += 1
        vector_candidates = vector_candidates_clean
        
        # 4. Candidate Union & Deduplication
        merged = {}
        
        # Add vector candidates
        for vc in vector_candidates:
            mat_id = vc["material_id"]
            merged[mat_id] = {
                "material_id": mat_id,
                "cpse_id": "", 
                "retrieval_sources": ["VECTOR"],
                "vector_similarity": vc["vector_similarity"],
                "bm25_score": None
            }
            
        # Add/Update with lexical candidates
        for lc in lexical_candidates:
            mat_id = lc["material_id"]
            if mat_id in merged:
                merged[mat_id]["retrieval_sources"].append("BM25")
                merged[mat_id]["bm25_score"] = lc["bm25_score"]
            else:
                merged[mat_id] = {
                    "material_id": mat_id,
                    "cpse_id": "",
                    "retrieval_sources": ["BM25"],
                    "vector_similarity": None,
                    "bm25_score": lc["bm25_score"]
                }
                
        # Calculate Overlap metrics
        bm25_only = sum(1 for v in merged.values() if v["retrieval_sources"] == ["BM25"])
        vector_only = sum(1 for v in merged.values() if v["retrieval_sources"] == ["VECTOR"])
        overlap = sum(1 for v in merged.values() if "BM25" in v["retrieval_sources"] and "VECTOR" in v["retrieval_sources"])
        union_count = len(merged)
        duplicates_removed = (len(vector_candidates) + len(lexical_candidates)) - union_count
        
        # 5. Build Final Candidate Objects
        def _sort_key(c_dict):
            source_count = len(c_dict["retrieval_sources"])
            vec_sim = c_dict["vector_similarity"] or -1.0
            bm25 = c_dict["bm25_score"] or -1.0
            return (source_count, vec_sim, bm25)
            
        sorted_dicts = sorted(list(merged.values()), key=_sort_key, reverse=True)
        
        # Limit to final top_k
        final_dicts = sorted_dicts[:top_k]
        
        candidates = []
        for i, c in enumerate(final_dicts):
            candidates.append(Candidate(
                material_id=c["material_id"],
                cpse_id=c["cpse_id"], 
                retrieval_sources=c["retrieval_sources"],
                bm25_score=c["bm25_score"],
                vector_similarity=c["vector_similarity"],
                retrieval_rank=i + 1,
                retrieval_version=self.retrieval_version,
                representation_version=self.representation_builder.version,
                embedding_model="Qwen3-Embedding-0.6B",
                embedding_version="1.0"
            ))
            
        return CandidateSet(
            query_material_id=query_id,
            candidates=candidates,
            metadata={
                "bm25_only": bm25_only,
                "vector_only": vector_only,
                "overlap": overlap,
                "union_count": union_count,
                "self_matches_removed": self_matches_removed,
                "duplicates_removed": duplicates_removed
            }
        )
