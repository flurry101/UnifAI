import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class Provenance(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    source_type: str
    source_system: str
    source_record_id: str
    source_file: str
    source_row: int
    ingestion_timestamp: str
    processing_version: str

class UnifiedMaterialRecord(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    # 1. Identity
    original_material_code: Optional[str] = Field(None, validation_alias='material_code')
    cpse: Optional[str] = Field(None, validation_alias='cpse_id')
    source_system: Optional[str] = None
    
    # 2. Description
    original_description: str = Field(..., validation_alias='description_original')
    normalized_description: Optional[str] = None
    
    # 3. Classification
    material_type: Optional[str] = None
    material_group: Optional[str] = None
    commodity_class: Optional[str] = None
    
    # 4. Basic material information
    material: Optional[str] = None
    material_grade: Optional[str] = Field(None, validation_alias='grade')
    standard: Optional[str] = None
    
    # 5. Technical attributes
    nominal_size: Optional[str] = None
    size_unit: Optional[str] = None
    pressure_class: Optional[str] = None
    pressure_class_system: Optional[str] = None
    pressure_unit: Optional[str] = None
    schedule: Optional[str] = None
    thickness: Optional[float] = None
    thickness_unit: Optional[str] = None
    voltage: Optional[float] = None
    voltage_unit: Optional[str] = None
    temperature_rating: Optional[float] = None
    temperature_unit: Optional[str] = None
    thread_type: Optional[str] = Field(None, validation_alias='thread')
    face_type: Optional[str] = None
    connection_type: Optional[str] = None
    outer_diameter: Optional[float] = None
    outer_diameter_unit: Optional[str] = None
    cross_section: Optional[float] = None
    cross_section_unit: Optional[str] = None
    cores: Optional[int] = None
    length: Optional[float] = None
    length_unit: Optional[str] = None
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    
    # 6. Commercial/reference fields
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    canonical_uom: Optional[str] = Field(None, validation_alias='base_uom')
    criticality: Optional[str] = None
    
    # 7. Provenance
    provenance: Provenance
    
    # 8. Extraction Evidence
    source_conflict: bool = False
    source_conflicts: dict = Field(default_factory=dict)
    ambiguities: dict = Field(default_factory=dict)
    extraction_metadata: dict = Field(default_factory=dict)
    
    # Note: explicit removal of canonical_id, expected_relationship, etc.

    def to_dict(self):
        d = self.model_dump()
        prov = d.pop('provenance')
        return {**d, **prov}
