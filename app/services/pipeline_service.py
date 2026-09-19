from sqlalchemy.orm import Session
from sqlalchemy import text
from src.retrieval.vector_store import PostgresVectorStore
from src.retrieval.embeddings import Qwen3EmbeddingProvider
from src.retrieval.lexical import LexicalRetriever
from src.retrieval.engine import RetrievalEngine
from src.matching.lane6_features import PairFeatureEngine
from src.ml.predictor import Lane7Predictor
from src.matching.lane8_decision import Lane8DecisionEngine
from src.matching.models import Pair
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from app.models import MatchProposal
import json

# Initialize engines lazily to avoid loading heavy models on startup if not used
_retrieval_engine = None
_pair_feature_engine = None
_lane7_predictor = None
_lane8_decision = None

def _get_engines():
    global _retrieval_engine, _pair_feature_engine, _lane7_predictor, _lane8_decision
    if _retrieval_engine is None:
        vector_store = PostgresVectorStore()
        embedding_provider = Qwen3EmbeddingProvider()
        lexical = LexicalRetriever()
        lexical.refresh(vector_store.get_all_materials()) # initialize BM25
        _retrieval_engine = RetrievalEngine(vector_store, embedding_provider, lexical)
        _pair_feature_engine = PairFeatureEngine()
        _lane7_predictor = Lane7Predictor("artifacts/matching_model")
        _lane8_decision = Lane8DecisionEngine()
    return _retrieval_engine, _pair_feature_engine, _lane7_predictor, _lane8_decision

def _row_to_record(row) -> UnifiedMaterialRecord:
    """Helper to convert material_retrieval row to UnifiedMaterialRecord"""
    prov = Provenance(
        source_type=row.source_type or "DB",
        source_system=row.source_system or "ERP",
        source_record_id=row.material_id,
        source_file=row.source_file or "db",
        source_row=row.source_row or 0,
        ingestion_timestamp=row.ingestion_timestamp or "2026",
        processing_version=row.processing_version or "v1"
    )
    return UnifiedMaterialRecord(
        material_code=row.original_material_code,
        cpse_id=row.cpse_id,
        description_original=row.normalized_description or "", # Use normalized as fallback
        normalized_description=row.normalized_description,
        provenance=prov
    )

def match_material(material_id: str, db: Session):
    """
    Orchestrate Lanes 5-8 for a given material_id.
    """
    # 1. Fetch query material from Lane 5 table
    query_text = text("SELECT * FROM material_retrieval WHERE material_id = :id")
    row = db.execute(query_text, {"id": material_id}).fetchone()
    if not row:
        raise ValueError(f"Material {material_id} not found in retrieval store")
        
    query_record = _row_to_record(row)
    
    # 2. Get engines
    retrieval, pair_engine, lane7, lane8 = _get_engines()
    
    # 3. Lane 5: Retrieval
    candidate_set = retrieval.retrieve_candidates(query_record, top_k=5)
    
    proposals = []
    
    # 4. Process each candidate
    for cand in candidate_set.candidates:
        cand_row = db.execute(query_text, {"id": cand.material_id}).fetchone()
        if not cand_row:
            continue
            
        cand_record = _row_to_record(cand_row)
        
        # Lane 6: Pair Features
        pair = Pair(query_material=query_record, candidate_material=cand_record)
        feature_result = pair_engine.evaluate(pair)
        
        # Lane 7: ML Prediction
        ml_result = lane7.predict_relationship(feature_result)
        
        # Lane 8: Safety & Governance Decision
        decision = lane8.decide(feature_result, ml_result["probabilities"])
        
        # Save MatchProposal to DB
        proposal = MatchProposal(
            query_material_id=material_id,
            candidate_material_id=cand.material_id,
            predicted_relation=decision.final_relation,
            confidence_level=decision.confidence_level,
            decision_status=decision.decision_status,
            governance_state="PENDING",
            lane7_probabilities=decision.model_probabilities,
            lane8_decision={
                "explanation": decision.explanation,
                "safety_rule_triggered": decision.safety_rule_triggered,
                "review_reason": decision.review_reason
            },
            model_version="Lane7-v1+Lane8-v1"
        )
        db.add(proposal)
        proposals.append(proposal)
        
    db.commit()
    
    return proposals

