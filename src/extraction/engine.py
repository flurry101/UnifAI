from typing import List, Dict, Any
from src.ingestion.unified_schema import UnifiedMaterialRecord
from src.extraction.extractors import (
    extract_commodity,
    extract_material,
    extract_standard_and_grade,
    extract_dimensions,
    extract_pressure,
    extract_electrical,
    extract_connections,
    extract_manufacturer
)

class ExtractionEngine:
    def __init__(self):
        self.extractors = [
            extract_commodity,
            extract_material,
            extract_standard_and_grade,
            extract_dimensions,
            extract_pressure,
            extract_electrical,
            extract_connections,
            extract_manufacturer
        ]

    def process(self, record: UnifiedMaterialRecord) -> UnifiedMaterialRecord:
        """Run extraction logic and manage metadata/conflicts."""
        if not getattr(record, 'normalized_description', None):
            return record
            
        desc = record.normalized_description
        
        # 1. Gather all extractions
        all_extractions = {}
        for func in self.extractors:
            results = func(desc)
            if not results:
                continue
            for attr_name, items in results.items():
                if not items:
                    continue
                if attr_name not in all_extractions:
                    all_extractions[attr_name] = []
                all_extractions[attr_name].extend(items)
                
        # 2. Resolve and apply extractions
        for attr_name, items in all_extractions.items():
            if not items:
                continue
                
            # If multiple distinct values are found for the same attribute, we preserve ambiguity
            unique_values = list({item['value'] for item in items})
            
            if len(unique_values) > 1:
                # Ambiguity conflict (multiple distinct values in text)
                record.ambiguities[attr_name] = {
                    "type": "MULTIPLE_EXTRACTIONS",
                    "values": unique_values,
                    "evidence": items
                }
                # Do not silently overwrite or guess. We leave the model's attribute empty or as is
                continue
                
            # Single value resolved
            best_item = items[0]
            val = best_item['value']
            
            # Check for conflict with existing structured data
            existing_val = getattr(record, attr_name, None)
            
            if existing_val is not None:
                # Normalization or type casting for comparison
                try:
                    if isinstance(existing_val, float):
                        cmp_existing = float(existing_val)
                        cmp_val = float(val)
                    else:
                        cmp_existing = str(existing_val).strip().upper()
                        cmp_val = str(val).strip().upper()
                except Exception:
                    cmp_existing = existing_val
                    cmp_val = val
                    
                if cmp_existing != cmp_val:
                    # Source conflict
                    record.source_conflict = True
                    record.source_conflicts[attr_name] = {
                        "type": "STRUCTURED_VS_DESCRIPTION",
                        "structured_value": existing_val,
                        "extracted_value": val,
                        "extracted_text": best_item['source_text']
                    }
                    # We do NOT overwrite existing structured fields. 
                    # We just log the conflict and store evidence
                    record.extraction_metadata[attr_name] = best_item
                    continue
                    
            # Safe to apply
            if hasattr(record, attr_name):
                setattr(record, attr_name, val)
                record.extraction_metadata[attr_name] = best_item
                
        return record
