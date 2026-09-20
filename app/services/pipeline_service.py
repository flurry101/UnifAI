import os
import json
import logging
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

logger = logging.getLogger(__name__)

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

def _local_match_candidates(query_row, all_candidates, db: Session):
    """
    Fallback deterministic matching engine when external neural models (HuggingFace/Postgres) are offline.
    Evaluates lexical token overlap and technical attributes across local.db materials,
    persisting real MatchProposal records.
    """
    query_id = query_row.material_id
    query_desc = (query_row.normalized_description or query_row.original_material_code or "").upper()
    query_tokens = set(query_desc.replace('/', ' ').replace('-', ' ').replace(',', ' ').split())

    scored_candidates = []
    for cand in all_candidates:
        if cand.material_id == query_id:
            continue
        cand_desc = (cand.normalized_description or cand.original_material_code or "").upper()
        cand_tokens = set(cand_desc.replace('/', ' ').replace('-', ' ').replace(',', ' ').split())

        intersection = query_tokens.intersection(cand_tokens)
        union = query_tokens.union(cand_tokens)
        jaccard = len(intersection) / len(union) if union else 0.0

        # Check for key domain keywords
        key_matches = [w for w in ["CYLINDER", "VALVE", "PIPE", "TUBE", "FLANGE", "14.2", "DN100", "6IN", "IS:3196", "API"] if w in query_desc and w in cand_desc]
        score = jaccard + 0.3 * len(key_matches)
        scored_candidates.append((cand, score, jaccard, key_matches))

    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = scored_candidates[:3]

    proposals = []
    for cand, score, jaccard, key_matches in top_candidates:
        cand_desc = (cand.normalized_description or "").upper()

        # Determine relation
        if jaccard > 0.6 or (len(key_matches) >= 2 and jaccard > 0.35):
            relation = "IDENTICAL"
            conf = "HIGH"
            decision_status = "PROPOSED"
            identical_score = min(1.0, jaccard + 0.1 * len(key_matches))
            lane7_probs = {"IDENTICAL": identical_score, "EQUIVALENT": 0.0, "VARIANT_OF": 0.0, "DISTINCT": 1.0 - identical_score}
            explanation = "High lexical and technical parameter alignment across CPSE catalogs."
        elif jaccard > 0.3 or len(key_matches) >= 1:
            relation = "EQUIVALENT" if "CYLINDER" in key_matches or "PIPE" in key_matches else "VARIANT_OF"
            conf = "MEDIUM"
            decision_status = "REVIEW"
            equivalent_score = min(1.0, jaccard + 0.1 * len(key_matches))
            lane7_probs = {
                "IDENTICAL": 0.0,
                "EQUIVALENT": equivalent_score if relation == "EQUIVALENT" else 1.0 - equivalent_score,
                "VARIANT_OF": equivalent_score if relation == "VARIANT_OF" else 1.0 - equivalent_score,
                "DISTINCT": 0.0,
            }
            explanation = "Shared functional category with variance in operational attributes."
        else:
            relation = "DISTINCT"
            conf = "HIGH"
            decision_status = "REVIEW"
            lane7_probs = {"IDENTICAL": 0.0, "EQUIVALENT": 0.0, "VARIANT_OF": 0.0, "DISTINCT": 1.0}
            explanation = "Commodity class and functional specifications diverge."

        # Check existing proposal
        existing = db.query(MatchProposal).filter(
            MatchProposal.query_material_id == query_id,
            MatchProposal.candidate_material_id == cand.material_id
        ).first()

        if existing:
            proposals.append(existing)
            continue

        proposal = MatchProposal(
            query_material_id=query_id,
            candidate_material_id=cand.material_id,
            predicted_relation=relation,
            confidence_level=conf,
            decision_status=decision_status,
            governance_state="PENDING",
            lane7_probabilities=lane7_probs,
            lane8_decision={
                "explanation": explanation,
                "safety_rule_triggered": decision_status == "REVIEW",
                "review_reason": "Dual-human validation required for cross-CPSE linkage." if decision_status == "REVIEW" else "Direct candidate mapping suggested.",
                "is_heuristic": True,
                "jaccard": jaccard,
                "key_matches": key_matches,
            },
            model_version="Heuristic-Local-v1+Lane8-v1"
        )
        db.add(proposal)
        proposals.append(proposal)

    db.commit()
    return proposals

def match_material(material_id: str, db: Session):
    """
    Orchestrate Lanes 5-8 for a given material_id.
    Persists real MatchProposal records to database.
    """
    # 1. Fetch query material from Lane 5 table (support exact or prefix)
    query_text = text("""
        SELECT material_id, cpse_id, original_material_code, normalized_description, source_system,
               source_type, source_record_id, source_file, source_row, ingestion_timestamp, processing_version
        FROM material_retrieval
        WHERE material_id = :id OR original_material_code = :id OR material_id LIKE :prefix
        LIMIT 1
    """)
    row = db.execute(query_text, {"id": material_id, "prefix": f"{material_id}%"}).fetchone()
    if not row:
        raise ValueError(f"Material {material_id} not found in retrieval store")
        
    actual_material_id = row[0]
    
    # Check if proposals already exist in database for this query material
    existing_proposals = db.query(MatchProposal).filter(MatchProposal.query_material_id == actual_material_id).all()
    if existing_proposals:
        return existing_proposals

    # 2. Check if local database / offline mode is active for instant zero-latency matching
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("sqlite") or os.getenv("USE_LOCAL_PIPELINE", "0") == "1":
        all_cands_query = text("""
            SELECT material_id, cpse_id, original_material_code, normalized_description, source_system,
                   source_type, source_record_id, source_file, source_row, ingestion_timestamp, processing_version
            FROM material_retrieval
            WHERE material_id != :id
            LIMIT 50
        """)
        all_candidates = db.execute(all_cands_query, {"id": actual_material_id}).fetchall()
        return _local_match_candidates(row, all_candidates, db)

    # Otherwise try neural engine with fallback
    try:
        query_record = _row_to_record(row)
        retrieval, pair_engine, lane7, lane8 = _get_engines()
        candidate_set = retrieval.retrieve_candidates(query_record, top_k=5)
        
        proposals = []
        for cand in candidate_set.candidates:
            cand_row = db.execute(query_text, {"id": cand.material_id, "prefix": f"{cand.material_id}%"}).fetchone()
            if not cand_row:
                continue
                
            cand_record = _row_to_record(cand_row)
            pair = Pair(query_material=query_record, candidate_material=cand_record)
            feature_result = pair_engine.evaluate(pair)
            ml_result = lane7.predict_relationship(feature_result)
            decision = lane8.decide(feature_result, ml_result["probabilities"])
            
            proposal = MatchProposal(
                query_material_id=actual_material_id,
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
    except Exception:
        logger.exception("Neural matching pipeline failed; using deterministic fallback")
        db.rollback()
        # Fallback to local database matching across material_retrieval
        all_cands_query = text("""
            SELECT material_id, cpse_id, original_material_code, normalized_description, source_system,
                   source_type, source_record_id, source_file, source_row, ingestion_timestamp, processing_version
            FROM material_retrieval
            WHERE material_id != :id
            LIMIT 50
        """)
        all_candidates = db.execute(all_cands_query, {"id": actual_material_id}).fetchall()
        return _local_match_candidates(row, all_candidates, db)
