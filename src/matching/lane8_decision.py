"""
Lane 8: Safety, Confidence and Human-Review Decision Engine — UnifAI SIH26099

Deterministic safety and decision layer that consumes:
  - Lane 7 class probabilities (weighted LightGBM)
  - Lane 6 structured evidence (PairFeatureResult)

and produces:
  - final relationship
  - confidence level
  - decision status
  - machine-readable evidence
  - human-readable explanation

Lane 8 is NOT another classifier. It is a governance layer.

INVARIANTS:
  1. A hard technical conflict CANNOT be auto-accepted as IDENTICAL or EQUIVALENT.
  2. A high LightGBM probability alone CANNOT override a hard technical conflict.
  3. Missing information CANNOT automatically become a technical conflict.
"""

from typing import Dict, List, Optional
import numpy as np

from src.matching.models import PairFeatureResult
from src.matching.lane8_models import Lane8Decision, EvidenceItem


# ---------------------------------------------------------------
# Confidence thresholds (empirically motivated from Lane 7D)
# ---------------------------------------------------------------
# Lane 7D validation showed:
#   Mean P(IDENTICAL) for true IDENTICAL ≈ 0.46
#   Mean P(EQUIVALENT) for true EQUIVALENT ≈ 0.31
#   Mean P(VARIANT_OF) for true VARIANT_OF ≈ 0.21
#   Max P(VARIANT_OF) for true VARIANT_OF ≈ 0.89
# These are conservative thresholds derived from the experiment.

HIGH_CONFIDENCE_THRESHOLD = 0.60     # strong model + evidence agreement
MEDIUM_CONFIDENCE_THRESHOLD = 0.35   # decent model signal
LOW_CONFIDENCE_THRESHOLD = 0.15      # weak but non-trivial signal
MIN_MARGIN = 0.10                    # minimum gap between top-1 and top-2


class Lane8DecisionEngine:
    """
    Deterministic safety and decision engine.

    Decision cascade:
      1. Read Lane 7 probabilities
      2. Determine top predicted relationship
      3. Check Lane 6 hard technical conflicts
      4. Check relationship-specific evidence
      5. Check missing critical evidence
      6. Check confidence and probability margin
      7. Produce final decision
    """

    def decide(
        self,
        feature_result: PairFeatureResult,
        model_probabilities: Dict[str, float],
    ) -> Lane8Decision:
        """
        Produce a Lane 8 decision from Lane 6 features + Lane 7 probabilities.

        Args:
            feature_result: PairFeatureResult from Lane 6
            model_probabilities: dict of {class_name: probability} from Lane 7
        """
        # Step 1: Read probabilities
        probs = model_probabilities
        sorted_probs = sorted(probs.items(), key=lambda x: -x[1])
        top_class = sorted_probs[0][0]
        top_prob = sorted_probs[0][1]
        second_prob = sorted_probs[1][1] if len(sorted_probs) > 1 else 0.0
        margin = top_prob - second_prob

        # Step 2: Collect evidence
        evidence = self._collect_evidence(feature_result)
        missing = self._collect_missing(feature_result)

        # Step 3: Check hard technical conflicts
        has_conflict = feature_result.technical_conflict
        conflict_fields = self._get_conflict_fields(feature_result)
        blocking_reasons = []

        if has_conflict:
            for cf in conflict_fields:
                blocking_reasons.append(f"Technical conflict: {cf}")

        # Step 4-7: Decision cascade
        safety_triggered = False
        final_relation = top_class
        confidence = "REVIEW"
        status = "REVIEW"
        review_reason = ""
        human_review = False

        # -------------------------------------------------------
        # SAFETY GATE: Hard conflicts block IDENTICAL/EQUIVALENT
        # -------------------------------------------------------
        if has_conflict and top_class in ("IDENTICAL", "EQUIVALENT"):
            safety_triggered = True
            final_relation = "UNDETERMINED"
            confidence = "REVIEW"
            status = "REVIEW"
            human_review = True
            review_reason = "TECHNICAL_CONFLICT"

        # SAFETY GATE: Hard conflicts block VARIANT_OF
        elif has_conflict and top_class == "VARIANT_OF":
            safety_triggered = True
            final_relation = "UNDETERMINED"
            confidence = "REVIEW"
            status = "REVIEW"
            human_review = True
            review_reason = "TECHNICAL_CONFLICT"

        # -------------------------------------------------------
        # DISTINCT prediction
        # -------------------------------------------------------
        elif top_class == "DISTINCT":
            final_relation = "DISTINCT"
            if top_prob >= HIGH_CONFIDENCE_THRESHOLD:
                confidence = "HIGH"
                status = "PROPOSED"
            elif top_prob >= MEDIUM_CONFIDENCE_THRESHOLD:
                confidence = "MEDIUM"
                status = "PROPOSED"
            else:
                confidence = "LOW"
                status = "REVIEW"
                human_review = True
                review_reason = "LOW_MODEL_CONFIDENCE"

        # -------------------------------------------------------
        # UNDETERMINED prediction
        # -------------------------------------------------------
        elif top_class == "UNDETERMINED":
            final_relation = "UNDETERMINED"
            confidence = "REVIEW"
            status = "REVIEW"
            human_review = True
            review_reason = "MODEL_UNDETERMINED"

        # -------------------------------------------------------
        # POSITIVE PREDICTIONS (no conflict)
        # -------------------------------------------------------
        elif top_class == "IDENTICAL":
            final_relation, confidence, status, human_review, review_reason = \
                self._evaluate_identical(feature_result, top_prob, margin, missing)

        elif top_class == "EQUIVALENT":
            final_relation, confidence, status, human_review, review_reason = \
                self._evaluate_equivalent(feature_result, top_prob, margin, missing)

        elif top_class == "VARIANT_OF":
            final_relation, confidence, status, human_review, review_reason = \
                self._evaluate_variant(feature_result, top_prob, margin, missing)

        # Build explanation
        explanation = self._build_explanation(
            final_relation, top_class, confidence, status,
            has_conflict, conflict_fields, missing, review_reason
        )

        recommended_action = self._recommend_action(final_relation, confidence, status)

        return Lane8Decision(
            final_relation=final_relation,
            confidence_level=confidence,
            decision_status=status,
            model_predicted_relation=top_class,
            model_probabilities=probs,
            technical_conflict=has_conflict,
            safety_rule_triggered=safety_triggered,
            blocking_reasons=blocking_reasons,
            evidence=evidence,
            missing_critical_attributes=missing,
            human_review_required=human_review,
            review_reason=review_reason,
            recommended_action=recommended_action,
            explanation=explanation,
        )

    # ---------------------------------------------------------------
    # RELATIONSHIP-SPECIFIC EVALUATION
    # ---------------------------------------------------------------
    def _evaluate_identical(self, fr: PairFeatureResult, prob: float,
                            margin: float, missing: List[str]):
        """Evaluate IDENTICAL prediction (no conflict already checked)."""
        # Count matching technical attributes
        tech_matches = self._count_tech_matches(fr)
        tech_evaluated = self._count_tech_evaluated(fr)

        # IDENTICAL requires strong evidence
        if prob >= HIGH_CONFIDENCE_THRESHOLD and margin >= MIN_MARGIN and tech_matches >= 2:
            return "IDENTICAL", "HIGH", "PROPOSED", False, ""

        if prob >= MEDIUM_CONFIDENCE_THRESHOLD and tech_matches >= 1:
            if len(missing) <= 3:
                return "IDENTICAL", "MEDIUM", "PROPOSED", False, ""
            else:
                return "IDENTICAL", "LOW", "REVIEW", True, "MISSING_CRITICAL_ATTRIBUTE"

        if prob >= LOW_CONFIDENCE_THRESHOLD:
            return "IDENTICAL", "LOW", "REVIEW", True, "LOW_MODEL_CONFIDENCE"

        return "UNDETERMINED", "REVIEW", "REVIEW", True, "INSUFFICIENT_TECHNICAL_EVIDENCE"

    def _evaluate_equivalent(self, fr: PairFeatureResult, prob: float,
                             margin: float, missing: List[str]):
        """Evaluate EQUIVALENT prediction (no conflict already checked)."""
        tech_matches = self._count_tech_matches(fr)

        if prob >= HIGH_CONFIDENCE_THRESHOLD and margin >= MIN_MARGIN and tech_matches >= 1:
            return "EQUIVALENT", "HIGH", "PROPOSED", False, ""

        if prob >= MEDIUM_CONFIDENCE_THRESHOLD and tech_matches >= 1:
            return "EQUIVALENT", "MEDIUM", "PROPOSED", False, ""

        if prob >= MEDIUM_CONFIDENCE_THRESHOLD:
            # Model is reasonably confident but no tech match evidence
            if fr.semantic_similarity >= 0.90:
                return "EQUIVALENT", "LOW", "REVIEW", True, "INSUFFICIENT_TECHNICAL_EVIDENCE"
            return "UNDETERMINED", "REVIEW", "REVIEW", True, "INSUFFICIENT_TECHNICAL_EVIDENCE"

        if prob >= LOW_CONFIDENCE_THRESHOLD:
            return "EQUIVALENT", "LOW", "REVIEW", True, "LOW_MODEL_CONFIDENCE"

        return "UNDETERMINED", "REVIEW", "REVIEW", True, "INSUFFICIENT_TECHNICAL_EVIDENCE"

    def _evaluate_variant(self, fr: PairFeatureResult, prob: float,
                          margin: float, missing: List[str]):
        """Evaluate VARIANT_OF prediction (no conflict already checked)."""
        tech_matches = self._count_tech_matches(fr)

        # VARIANT_OF: base identity matches + additional info
        has_variant_evidence = (
            fr.additional_attribute_count > 0 or
            tech_matches >= 1
        )

        if prob >= HIGH_CONFIDENCE_THRESHOLD and has_variant_evidence:
            return "VARIANT_OF", "HIGH", "PROPOSED", False, ""

        if prob >= MEDIUM_CONFIDENCE_THRESHOLD and has_variant_evidence:
            return "VARIANT_OF", "MEDIUM", "PROPOSED", False, ""

        if prob >= LOW_CONFIDENCE_THRESHOLD:
            if has_variant_evidence:
                return "VARIANT_OF", "LOW", "REVIEW", True, "LOW_MODEL_CONFIDENCE"
            return "UNDETERMINED", "REVIEW", "REVIEW", True, "INSUFFICIENT_TECHNICAL_EVIDENCE"

        return "UNDETERMINED", "REVIEW", "REVIEW", True, "INSUFFICIENT_TECHNICAL_EVIDENCE"

    # ---------------------------------------------------------------
    # EVIDENCE COLLECTION
    # ---------------------------------------------------------------
    def _collect_evidence(self, fr: PairFeatureResult) -> List[EvidenceItem]:
        """Collect all available evidence from PairFeatureResult."""
        items = []

        # Semantic similarity
        items.append(EvidenceItem(
            evidence_type="SEMANTIC_SIMILARITY",
            field="semantic_similarity",
            detail=f"Semantic similarity: {fr.semantic_similarity:.4f}",
            score=fr.semantic_similarity,
        ))

        # Lexical similarity
        items.append(EvidenceItem(
            evidence_type="LEXICAL_MATCH",
            field="lexical_similarity",
            detail=f"Lexical (BM25) similarity: {fr.lexical_similarity:.2f}",
            score=fr.lexical_similarity,
        ))

        # Three-state attribute evidence
        attr_map = {
            "dimension": fr.dimension_match,
            "pressure_rating": fr.pressure_rating_match,
            "material_grade": fr.material_grade_match,
            "standard": fr.standard_match,
            "component_type": fr.component_type_match,
            "manufacturer": fr.manufacturer_match,
            "mpn": fr.mpn_match,
            "uom": fr.uom_compatibility,
        }

        for field_name, value in attr_map.items():
            if value is True:
                items.append(EvidenceItem(
                    evidence_type="EXACT_ATTRIBUTE_MATCH",
                    field=field_name,
                    detail=f"{field_name} matches",
                    match=True,
                ))
            elif value is False:
                items.append(EvidenceItem(
                    evidence_type="TECHNICAL_CONFLICT",
                    field=field_name,
                    detail=f"{field_name} conflicts",
                    match=False,
                ))
            # None = missing, handled separately

        # Technical conflict (aggregate)
        if fr.technical_conflict:
            items.append(EvidenceItem(
                evidence_type="TECHNICAL_CONFLICT",
                field="technical_conflict",
                detail="Hard technical conflict detected (aggregate)",
                match=False,
            ))

        # UOM compatibility
        if fr.uom_compatibility is True:
            items.append(EvidenceItem(
                evidence_type="UOM_COMPATIBILITY",
                field="uom",
                detail="UOM compatible",
                match=True,
            ))

        return items

    def _collect_missing(self, fr: PairFeatureResult) -> List[str]:
        """Collect list of missing critical attributes."""
        missing = []
        if fr.missing_dimension:
            missing.append("dimension")
        if fr.missing_pressure:
            missing.append("pressure_rating")
        if fr.missing_material:
            missing.append("material_grade")
        if fr.missing_standard:
            missing.append("standard")
        if fr.missing_component:
            missing.append("component_type")
        return missing

    def _get_conflict_fields(self, fr: PairFeatureResult) -> List[str]:
        """Get list of specific conflict fields."""
        conflicts = []
        if fr.dimension_conflict:
            conflicts.append("dimension")
        if fr.pressure_conflict:
            conflicts.append("pressure_rating")
        if fr.material_conflict:
            conflicts.append("material_grade")
        if fr.standard_conflict:
            conflicts.append("standard")
        if fr.component_conflict:
            conflicts.append("component_type")
        return conflicts

    def _count_tech_matches(self, fr: PairFeatureResult) -> int:
        """Count non-None True technical attribute matches."""
        attrs = [
            fr.dimension_match, fr.pressure_rating_match,
            fr.material_grade_match, fr.standard_match,
            fr.component_type_match,
        ]
        return sum(1 for a in attrs if a is True)

    def _count_tech_evaluated(self, fr: PairFeatureResult) -> int:
        """Count non-None technical attributes (True or False)."""
        attrs = [
            fr.dimension_match, fr.pressure_rating_match,
            fr.material_grade_match, fr.standard_match,
            fr.component_type_match,
        ]
        return sum(1 for a in attrs if a is not None)

    # ---------------------------------------------------------------
    # EXPLANATION GENERATION (deterministic templates)
    # ---------------------------------------------------------------
    def _build_explanation(self, final_rel, model_pred, confidence, status,
                           has_conflict, conflict_fields, missing, review_reason):
        """Build a deterministic human-readable explanation."""
        parts = []

        # Relationship statement
        if final_rel == model_pred:
            parts.append(f"{final_rel} -- {status}.")
        elif final_rel == "UNDETERMINED":
            parts.append(f"Model predicted {model_pred}, but decision is UNDETERMINED -- REVIEW required.")
        else:
            parts.append(f"Model predicted {model_pred}, final decision: {final_rel} -- {status}.")

        # Conflict explanation
        if has_conflict:
            fields_str = ", ".join(conflict_fields) if conflict_fields else "unspecified"
            parts.append(f"Technical conflict detected in: {fields_str}.")
            parts.append("Automatic positive relationship acceptance is blocked.")

        # Missing evidence
        if missing:
            missing_str = ", ".join(missing)
            parts.append(f"Missing technical information: {missing_str}.")

        # Review reason
        if review_reason:
            reason_map = {
                "TECHNICAL_CONFLICT": "Hard technical conflict requires human review.",
                "LOW_MODEL_CONFIDENCE": "Model confidence is low; human review recommended.",
                "INSUFFICIENT_TECHNICAL_EVIDENCE": "Insufficient technical evidence for automatic acceptance.",
                "MISSING_CRITICAL_ATTRIBUTE": "Critical attributes are missing; review recommended.",
                "SMALL_PROBABILITY_MARGIN": "Probability margin between top classes is small.",
                "MODEL_UNDETERMINED": "Model could not determine the relationship.",
            }
            parts.append(reason_map.get(review_reason, f"Review reason: {review_reason}."))

        return " ".join(parts)

    def _recommend_action(self, final_rel, confidence, status):
        """Recommend a human-readable action."""
        if status == "PROPOSED" and confidence in ("HIGH", "MEDIUM"):
            return f"Accept {final_rel} relationship (confidence: {confidence})."
        elif status == "REVIEW":
            return "Route to human reviewer for manual assessment."
        else:
            return f"Review {final_rel} decision (confidence: {confidence})."
