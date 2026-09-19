import numpy as np
from typing import Dict, Any
from src.matching.models import PairFeatureResult

def map_three_state(val: bool | None) -> float:
    """
    Map True -> 1.0, False -> 0.0, None -> np.nan.
    """
    if val is None:
        return np.nan
    return 1.0 if val else 0.0

def map_bool(val: bool) -> float:
    """Map explicit boolean to 1.0 / 0.0"""
    return 1.0 if val else 0.0

def extract_features(result: PairFeatureResult) -> Dict[str, float]:
    """
    Extract a flat numerical feature dictionary from PairFeatureResult for Lane 7 ML.
    """
    return {
        # 1. Retrieval
        "semantic_similarity": float(result.semantic_similarity),
        "lexical_similarity": float(result.lexical_similarity),
        
        # 2. Identity
        "manufacturer_match": map_three_state(result.manufacturer_match),
        "mpn_match": map_three_state(result.mpn_match),
        
        # 3. Component
        "component_type_match": map_three_state(result.component_type_match),
        
        # 4. Technical Comparisons
        "dimension_match": map_three_state(result.dimension_match),
        "pressure_rating_match": map_three_state(result.pressure_rating_match),
        "material_grade_match": map_three_state(result.material_grade_match),
        "standard_match": map_three_state(result.standard_match),
        "uom_compatibility": map_three_state(result.uom_compatibility),
        
        # 5. Conflicts
        "dimension_conflict": map_bool(result.dimension_conflict),
        "pressure_conflict": map_bool(result.pressure_conflict),
        "material_conflict": map_bool(result.material_conflict),
        "standard_conflict": map_bool(result.standard_conflict),
        "component_conflict": map_bool(result.component_conflict),
        "technical_conflict": map_bool(result.technical_conflict),
        
        # 6. Missing Information
        "missing_dimension": map_bool(result.missing_dimension),
        "missing_pressure": map_bool(result.missing_pressure),
        "missing_material": map_bool(result.missing_material),
        "missing_standard": map_bool(result.missing_standard),
        "missing_component": map_bool(result.missing_component),
        
        # 7. Additional Evidence
        "technical_attribute_overlap": float(result.technical_attribute_overlap),
        "additional_attribute_count": float(result.additional_attribute_count)
    }

def get_feature_names() -> list[str]:
    """Return the ordered list of feature names."""
    # Create a dummy result just to get the keys in order
    dummy = PairFeatureResult(
        semantic_similarity=0.0,
        lexical_similarity=0.0,
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
    return list(extract_features(dummy).keys())
