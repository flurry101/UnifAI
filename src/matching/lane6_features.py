from dataclasses import dataclass, field
from typing import Optional, List
from src.ingestion.unified_schema import UnifiedMaterialRecord
from src.matching.models import Pair, PairFeatureResult
from src.matching.attribute_extractors import (
    extract_dimension,
    extract_pressure,
    extract_material_grade,
    extract_standard,
    detect_technical_conflict
)
from src.matching.relationship_classifier import classify_relationship


class PairFeatureEngine:
    """
    Lane 6 Pair Feature Engine.
    Evaluates a Query and Candidate Pair to extract features and deterministically classify their relationship.
    """
    
    def evaluate(self, pair: Pair) -> PairFeatureResult:
        query_desc = pair.query_material.original_description.upper()
        cand_desc = pair.candidate_material.original_description.upper()
        
        # 1. Exact Identifier Features
        q_mfg = pair.query_material.manufacturer
        c_mfg = pair.candidate_material.manufacturer
        manufacturer_match = None
        if q_mfg and c_mfg:
            manufacturer_match = (q_mfg.strip().upper() == c_mfg.strip().upper())
            
        q_mpn = pair.query_material.manufacturer_part_number
        c_mpn = pair.candidate_material.manufacturer_part_number
        mpn_match = None
        if q_mpn and c_mpn:
            mpn_match = (q_mpn.strip().upper() == c_mpn.strip().upper())
            
        # 2. Extract technical parameters from descriptions
        q_dim = extract_dimension(query_desc)
        c_dim = extract_dimension(cand_desc)
        dimension_match = None
        if q_dim and c_dim:
            dimension_match = (q_dim == c_dim)
            
        q_press = extract_pressure(query_desc)
        c_press = extract_pressure(cand_desc)
        pressure_rating_match = None
        if q_press and c_press:
            pressure_rating_match = (q_press == c_press)
            
        q_mat = extract_material_grade(query_desc)
        c_mat = extract_material_grade(cand_desc)
        material_grade_match = None
        if q_mat and c_mat:
            material_grade_match = (q_mat == c_mat)
            
        q_std = extract_standard(query_desc)
        c_std = extract_standard(cand_desc)
        standard_match = None
        if q_std and c_std:
            standard_match = (q_std == c_std)
            
        # 3. Component match
        q_comp = None
        c_comp = None
        if "GATE" in query_desc and "VALVE" in query_desc: q_comp = "GATE VALVE"
        elif "GLOBE" in query_desc and "VALVE" in query_desc: q_comp = "GLOBE VALVE"
        elif "BALL" in query_desc and "VALVE" in query_desc: q_comp = "BALL VALVE"
        
        if "GATE" in cand_desc and "VALVE" in cand_desc: c_comp = "GATE VALVE"
        elif "GLOBE" in cand_desc and "VALVE" in cand_desc: c_comp = "GLOBE VALVE"
        elif "BALL" in cand_desc and "VALVE" in cand_desc: c_comp = "BALL VALVE"
        
        component_type_match = None
        if q_comp and c_comp:
            component_type_match = (q_comp == c_comp)
            
        uom_compatibility = None
        # Basic placeholder for uom compatibility
        if pair.query_material.canonical_uom and pair.candidate_material.canonical_uom:
            uom_compatibility = (pair.query_material.canonical_uom == pair.candidate_material.canonical_uom)

        # 4. Technical Conflict Flags
        dimension_conflict = (dimension_match is False)
        pressure_conflict = (pressure_rating_match is False)
        material_conflict = False
        standard_conflict = (standard_match is False)
        component_conflict = (component_type_match is False)

        if material_grade_match is False:
            # Check for compatible materials
            compatibles = [{"SS316", "316L"}, {"SS304", "304L"}]
            is_compatible = False
            for comp in compatibles:
                if q_mat in comp and c_mat in comp:
                    is_compatible = True
                    break
            if not is_compatible:
                material_conflict = True
                
        if detect_technical_conflict(query_desc, cand_desc):
            component_conflict = True
            
        technical_conflict = (dimension_conflict or pressure_conflict or material_conflict or standard_conflict or component_conflict)
        
        # 5. Missing Indicators
        missing_dimension = (q_dim is None and c_dim is None) or (dimension_match is None)
        missing_pressure = (q_press is None and c_press is None) or (pressure_rating_match is None)
        missing_material = (q_mat is None and c_mat is None) or (material_grade_match is None)
        missing_standard = (q_std is None and c_std is None) or (standard_match is None)
        missing_component = (q_comp is None and c_comp is None) or (component_type_match is None)
        
        # 6. Additional Evidence
        tech_attrs = [dimension_match, pressure_rating_match, material_grade_match, standard_match, component_type_match]
        evaluated_attrs = [x for x in tech_attrs if x is not None]
        technical_attribute_overlap = len(evaluated_attrs)
        
        additional_attribute_count = 0
        if len(cand_desc) > len(query_desc) + 6 or len(query_desc) > len(cand_desc) + 6:
            additional_attribute_count = 1

        # 7. Classify and Score
        return classify_relationship(
            pair=pair,
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
            additional_attribute_count=additional_attribute_count
        )
