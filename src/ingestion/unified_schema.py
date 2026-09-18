import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class Provenance:
    source_type: str
    source_system: str
    source_record_id: str
    source_file: str
    source_row: int
    ingestion_timestamp: str
    processing_version: str

@dataclass
class UnifiedMaterialRecord:
    # 1. Provenance
    provenance: Provenance
    
    # 2. Raw Source Data
    description_original: str
    base_uom: Optional[str] = None
    material_code: Optional[str] = None
    cpse_id: Optional[str] = None
    
    # 3. Normalized Data
    description_normalized: Optional[str] = None
    normalized_uom: Optional[str] = None
    
    # 4. Extracted Attributes (Fingerprint)
    commodity_class: Optional[str] = None
    material: Optional[str] = None
    grade: Optional[str] = None
    standard: Optional[str] = None
    nominal_size: Optional[str] = None
    size_unit: Optional[str] = None
    pressure_class: Optional[str] = None
    schedule: Optional[str] = None
    voltage: Optional[str] = None
    cores: Optional[str] = None
    cross_section: Optional[str] = None
    cross_section_unit: Optional[str] = None
    conductor: Optional[str] = None
    type: Optional[str] = None
    thread: Optional[str] = None
    
    # For synthetic only
    canonical_id: Optional[str] = None
    is_undetermined: Optional[bool] = False

    def to_dict(self):
        d = asdict(self)
        prov = d.pop('provenance')
        return {**d, **prov}
