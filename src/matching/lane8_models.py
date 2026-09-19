"""
Lane 8 Models — UnifAI SIH26099

Output models for the Lane 8 Safety, Confidence and Decision Engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class EvidenceItem:
    """A single piece of evidence supporting or blocking a decision."""
    evidence_type: str   # e.g. EXACT_ATTRIBUTE_MATCH, TECHNICAL_CONFLICT, MISSING_ATTRIBUTE
    field: str           # e.g. "pressure_class", "dimension", "semantic_similarity"
    detail: str          # human-readable detail
    match: Optional[bool] = None   # True=match, False=conflict, None=missing
    value_query: Optional[str] = None
    value_candidate: Optional[str] = None
    score: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "evidence_type": self.evidence_type,
            "field": self.field,
            "detail": self.detail,
        }
        if self.match is not None:
            d["match"] = self.match
        if self.value_query is not None:
            d["value_query"] = self.value_query
        if self.value_candidate is not None:
            d["value_candidate"] = self.value_candidate
        if self.score is not None:
            d["score"] = round(self.score, 6)
        return d


@dataclass
class Lane8Decision:
    """Complete Lane 8 decision output for a single candidate pair."""

    # Final decision
    final_relation: str           # IDENTICAL|EQUIVALENT|VARIANT_OF|DISTINCT|UNDETERMINED
    confidence_level: str         # HIGH|MEDIUM|LOW|REVIEW
    decision_status: str          # PROPOSED|REVIEW

    # Model outputs (preserved, never overwritten)
    model_predicted_relation: str
    model_probabilities: Dict[str, float]

    # Safety
    technical_conflict: bool
    safety_rule_triggered: bool
    blocking_reasons: List[str] = field(default_factory=list)

    # Evidence
    evidence: List[EvidenceItem] = field(default_factory=list)
    missing_critical_attributes: List[str] = field(default_factory=list)

    # Human governance
    human_review_required: bool = False
    review_reason: str = ""
    recommended_action: str = ""
    explanation: str = ""

    # Versioning
    model_version: str = "lane7d-weighted-v1"
    decision_version: str = "lane8-v1"

    def to_dict(self) -> dict:
        return {
            "final_relation": self.final_relation,
            "confidence_level": self.confidence_level,
            "decision_status": self.decision_status,
            "model_predicted_relation": self.model_predicted_relation,
            "model_probabilities": {k: round(v, 6) for k, v in self.model_probabilities.items()},
            "technical_conflict": self.technical_conflict,
            "safety_rule_triggered": self.safety_rule_triggered,
            "blocking_reasons": self.blocking_reasons,
            "evidence": [e.to_dict() for e in self.evidence],
            "missing_critical_attributes": self.missing_critical_attributes,
            "human_review_required": self.human_review_required,
            "review_reason": self.review_reason,
            "recommended_action": self.recommended_action,
            "explanation": self.explanation,
            "model_version": self.model_version,
            "decision_version": self.decision_version,
        }
