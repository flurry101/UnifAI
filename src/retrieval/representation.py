from src.ingestion.unified_schema import UnifiedMaterialRecord

class RetrievalRepresentationBuilder:
    def __init__(self, version: str = "v1"):
        self.version = version
        
        # We explicitly exclude manufacturer and MPN from this core representation
        self.fields = [
            "commodity_class",
            "material",
            "material_grade",
            "standard",
            "nominal_size",
            "size_unit",
            "thickness",
            "thickness_unit",
            "schedule",
            "pressure_class",
            "pressure_class_system",
            "voltage",
            "voltage_unit",
            "cores",
            "cross_section",
            "cross_section_unit",
            "face_type",
            "connection_type"
        ]

    def build(self, record: UnifiedMaterialRecord) -> str:
        """Builds a deterministic string representation for retrieval."""
        parts = []
        
        # We start with the normalized description
        if record.normalized_description:
            parts.append(record.normalized_description.strip())
            
        for field in self.fields:
            val = getattr(record, field, None)
            if val is not None:
                # Format to a nice string e.g. "Size: 4 IN"
                friendly_name = field.replace('_', ' ').title()
                parts.append(f"{friendly_name}: {val}")
        
        return "\n".join(parts)
