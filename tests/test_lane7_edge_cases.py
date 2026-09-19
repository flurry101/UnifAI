"""
Edge Case Tests for Lane 7 / Lane 8 Safety — UnifAI SIH26099
Tests the strict safety invariants required for material harmonization.
"""

import pytest
from src.matching.models import PairFeatureResult
from src.matching.lane8_decision import Lane8DecisionEngine
from src.ml.dataset import CLASSES

@pytest.fixture
def engine():
    return Lane8DecisionEngine()

def _create_base_fr():
    return PairFeatureResult(
        semantic_similarity=0.9,
        lexical_similarity=0.9,
        manufacturer_match=None,
        mpn_match=None,
        component_type_match=None,
        dimension_match=None,
        pressure_rating_match=None,
        material_grade_match=None,
        standard_match=None,
        uom_compatibility=None,
        dimension_conflict=False,
        pressure_conflict=False,
        material_conflict=False,
        standard_conflict=False,
        component_conflict=False,
        technical_conflict=False,
        missing_dimension=False,
        missing_pressure=False,
        missing_material=False,
        missing_standard=False,
        missing_component=False,
        technical_attribute_overlap=0,
        additional_attribute_count=0,
        relationship_score=0.0,
        relationship_class="UNDETERMINED",
        explanation=[]
    )

def _create_probs(predicted_class, confidence=0.9):
    probs = {cls: 0.01 for cls in CLASSES}
    probs[predicted_class] = confidence
    return probs

def test_case_1_identical(engine):
    """CASE 1: Same technical material expressed differently."""
    fr = _create_base_fr()
    fr.semantic_similarity = 0.95
    fr.dimension_match = True
    fr.material_grade_match = True
    
    probs = _create_probs("IDENTICAL", 0.95)
    decision = engine.decide(fr, probs)
    
    assert decision.final_relation == "IDENTICAL"
    assert not decision.safety_rule_triggered

def test_case_2_pressure_conflict(engine):
    """CASE 2: Same commodity but different pressure class."""
    fr = _create_base_fr()
    fr.semantic_similarity = 0.98
    fr.pressure_conflict = True
    fr.technical_conflict = True
    
    # Even if model is 99% confident it's IDENTICAL
    probs = _create_probs("IDENTICAL", 0.99)
    decision = engine.decide(fr, probs)
    
    assert decision.safety_rule_triggered
    assert decision.final_relation not in ("IDENTICAL", "EQUIVALENT")

def test_case_3_dimension_conflict(engine):
    """CASE 3: Same valve but different nominal dimension."""
    fr = _create_base_fr()
    fr.semantic_similarity = 0.95
    fr.dimension_conflict = True
    fr.technical_conflict = True
    
    # Model says EQUIVALENT with high confidence
    probs = _create_probs("EQUIVALENT", 0.90)
    decision = engine.decide(fr, probs)
    
    assert decision.safety_rule_triggered
    assert decision.final_relation not in ("IDENTICAL", "EQUIVALENT")

def test_case_4_variant(engine):
    """CASE 4: Same base technical identity with compatible additional info."""
    fr = _create_base_fr()
    fr.semantic_similarity = 0.85
    fr.additional_attribute_count = 2
    
    probs = _create_probs("VARIANT_OF", 0.80)
    decision = engine.decide(fr, probs)
    
    assert decision.final_relation == "VARIANT_OF"
    assert not decision.safety_rule_triggered

def test_case_5_missing_data(engine):
    """CASE 5: Very similar descriptions but missing critical technical fields."""
    fr = _create_base_fr()
    fr.semantic_similarity = 0.95
    fr.missing_dimension = True
    fr.missing_material = True
    
    probs = _create_probs("IDENTICAL", 0.60)
    decision = engine.decide(fr, probs)
    
    # Missing data does not automatically equal conflict
    assert not fr.technical_conflict
    # It might be REVIEW due to threshold
    assert decision.decision_status in ("PROPOSED", "REVIEW")

def test_case_6_high_sim_conflict(engine):
    """CASE 6: High semantic similarity + CONFLICT."""
    fr = _create_base_fr()
    fr.semantic_similarity = 0.99
    fr.technical_conflict = True
    
    probs = _create_probs("IDENTICAL", 0.99)
    decision = engine.decide(fr, probs)
    
    assert decision.safety_rule_triggered
    assert decision.final_relation not in ("IDENTICAL", "EQUIVALENT")

def test_case_7_mpn_match_conflict(engine):
    """CASE 7: MPN match but TECHNICAL CONFLICT."""
    fr = _create_base_fr()
    fr.mpn_match = True
    fr.technical_conflict = True
    
    probs = _create_probs("IDENTICAL", 0.99)
    decision = engine.decide(fr, probs)
    
    assert decision.safety_rule_triggered
    assert decision.final_relation not in ("IDENTICAL", "EQUIVALENT")

def test_case_8_different_components(engine):
    """CASE 8: Different component types."""
    fr = _create_base_fr()
    fr.semantic_similarity = 0.92
    fr.component_conflict = True
    fr.technical_conflict = True
    
    probs = _create_probs("IDENTICAL", 0.90)
    decision = engine.decide(fr, probs)
    
    assert decision.safety_rule_triggered
    assert decision.final_relation not in ("IDENTICAL", "EQUIVALENT")
