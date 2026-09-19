from dataclasses import dataclass
from typing import Optional, List
from src.ingestion.unified_schema import UnifiedMaterialRecord

@dataclass
class Pair:
    query_material: UnifiedMaterialRecord
    candidate_material: UnifiedMaterialRecord
    semantic_similarity: float
    lexical_similarity: float


@dataclass
class PairFeatureResult:
    # 1. Retrieval Features
    semantic_similarity: float
    lexical_similarity: float
    
    # 2. Identity Features
    manufacturer_match: Optional[bool]
    mpn_match: Optional[bool]
    
    # 3. Component Features
    component_type_match: Optional[bool]
    
    # 4. Technical Attribute Comparisons
    dimension_match: Optional[bool]
    pressure_rating_match: Optional[bool]
    material_grade_match: Optional[bool]
    standard_match: Optional[bool]
    uom_compatibility: Optional[bool]
    
    # 5. Technical Conflict Flags
    dimension_conflict: bool
    pressure_conflict: bool
    material_conflict: bool
    standard_conflict: bool
    component_conflict: bool
    technical_conflict: bool # Overall conflict (aggregate)
    
    # 6. Missing-Information Indicators
    missing_dimension: bool
    missing_pressure: bool
    missing_material: bool
    missing_standard: bool
    missing_component: bool
    
    # 7. Additional Evidence
    technical_attribute_overlap: int
    additional_attribute_count: int
    
    # 8. Deterministic Outputs (Auxiliary/Validation)
    relationship_score: float
    relationship_class: str
    explanation: List[str]
