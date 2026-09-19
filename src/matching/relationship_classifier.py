from typing import Optional, List
from src.matching.models import Pair, PairFeatureResult

def classify_relationship(
    pair: Pair,
    manufacturer_match: Optional[bool],
    mpn_match: Optional[bool],
    component_type_match: Optional[bool],
    dimension_match: Optional[bool],
    pressure_rating_match: Optional[bool],
    material_grade_match: Optional[bool],
    standard_match: Optional[bool],
    uom_compatibility: Optional[bool],
    dimension_conflict: bool,
    pressure_conflict: bool,
    material_conflict: bool,
    standard_conflict: bool,
    component_conflict: bool,
    technical_conflict: bool,
    missing_dimension: bool,
    missing_pressure: bool,
    missing_material: bool,
    missing_standard: bool,
    missing_component: bool,
    technical_attribute_overlap: int,
    additional_attribute_count: int
) -> PairFeatureResult:
    
    score = 0.0
    explanation = []
    
    # 1. Scoring (Only score available evidence)
    if mpn_match is True:
        score += 0.40
    elif mpn_match is False:
        score -= 0.40
        
    if manufacturer_match is True:
        score += 0.10
    elif manufacturer_match is False:
        score -= 0.10
        
    if dimension_match is True:
        score += 0.15
    elif dimension_match is False:
        score -= 0.25
        
    if pressure_rating_match is True:
        score += 0.15
    elif pressure_rating_match is False:
        score -= 0.25
        
    if material_grade_match is True:
        score += 0.10
    elif material_grade_match is False:
        score -= 0.25
        
    if standard_match is True:
        score += 0.10
    elif standard_match is False:
        score -= 0.25
        
    if technical_conflict:
        score -= 1.00
        explanation.append("Technical conflict detected.")
        
    # Bound score
    relationship_score = max(0.0, min(1.0, score + pair.semantic_similarity * 0.2)) # Give minor baseline from semantic
    
    
    # 2. Relationship Classification (Deterministic priority)
    
    tech_attrs = [dimension_match, pressure_rating_match, material_grade_match, standard_match]
    
    # "All available critical attributes match" means AT LEAST one critical attribute exists, and ALL that exist are True
    evaluated_attrs = [x for x in tech_attrs if x is not None]
    all_tech_match = (len(evaluated_attrs) > 0 and all(x is True for x in evaluated_attrs))
    
    q_desc = pair.query_material.original_description.upper()
    c_desc = pair.candidate_material.original_description.upper()
    
    has_extra_info = False
    # Simple heuristic for "one side contains additional compatible information"
    if len(c_desc) > len(q_desc) + 6 or len(q_desc) > len(c_desc) + 6:
        has_extra_info = True

    # PRIORITY 1: DISTINCT (Conflict)
    if technical_conflict:
        rel_class = "DISTINCT"
        explanation.append("Priority 1: Distinct due to explicit technical conflict.")
        
    # PRIORITY 2: IDENTICAL
    elif mpn_match is True or (all_tech_match and not has_extra_info and mpn_match is not False and manufacturer_match is not False):
        rel_class = "IDENTICAL"
        if mpn_match is True:
            explanation.append("Priority 2: Identical due to explicit MPN match.")
        else:
            explanation.append("Priority 2: Identical because all available critical technical attributes match.")
            
    # PRIORITY 3: VARIANT_OF
    elif technical_conflict is False and all_tech_match and has_extra_info:
        rel_class = "VARIANT_OF"
        explanation.append("Priority 3: Variant because core technical identity matches but additional compatible attributes exist.")
        
    # PRIORITY 4: EQUIVALENT
    elif technical_conflict is False and all_tech_match and (manufacturer_match is False or mpn_match is False):
        rel_class = "EQUIVALENT"
        explanation.append("Priority 4: Equivalent because technical properties match but manufacturer/MPN differs.")
        
    elif technical_conflict is False and (all_tech_match or (dimension_match is True and pressure_rating_match is True)):
        # If it wasn't identical (e.g. material grade was False but overridden by compatible materials)
        rel_class = "EQUIVALENT"
        explanation.append("Priority 4: Equivalent technical match (e.g., compatible materials).")
        
    # OTHERWISE: UNDETERMINED
    else:
        rel_class = "UNDETERMINED"
        explanation.append("Otherwise: Undetermined due to insufficient matches or multiple critical mismatches.")


    return PairFeatureResult(
        semantic_similarity=pair.semantic_similarity,
        lexical_similarity=pair.lexical_similarity,
        manufacturer_match=manufacturer_match,
        mpn_match=mpn_match,
        component_type_match=component_type_match,
        dimension_match=dimension_match,
        pressure_rating_match=pressure_rating_match,
        material_grade_match=material_grade_match,
        standard_match=standard_match,
        uom_compatibility=uom_compatibility,
        dimension_conflict=dimension_conflict,
        pressure_conflict=pressure_conflict,
        material_conflict=material_conflict,
        standard_conflict=standard_conflict,
        component_conflict=component_conflict,
        technical_conflict=technical_conflict,
        missing_dimension=missing_dimension,
        missing_pressure=missing_pressure,
        missing_material=missing_material,
        missing_standard=missing_standard,
        missing_component=missing_component,
        technical_attribute_overlap=technical_attribute_overlap,
        additional_attribute_count=additional_attribute_count,
        relationship_score=relationship_score,
        relationship_class=rel_class,
        explanation=explanation
    )
