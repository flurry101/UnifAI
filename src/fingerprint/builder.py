import hashlib
import json
from src.ingestion.unified_schema import UnifiedMaterialRecord
from src.fingerprint.schema import MaterialFingerprint

# Strict, fixed order of fields defining a material's technical identity.
# Changing this order or adding fields breaks schema v1 hashes!
FINGERPRINT_SCHEMA_VERSION = "v1"
IDENTITY_FIELDS = [
    "commodity_class",
    "material",
    "material_grade",
    "standard",
    "nominal_size",
    "size_unit",
    "outer_diameter",
    "outer_diameter_unit",
    "thickness",
    "thickness_unit",
    "schedule",
    "pressure_class",
    "pressure_class_system",
    "pressure_unit",
    "voltage",
    "voltage_unit",
    "temperature_rating",
    "temperature_unit",
    "thread_type",
    "face_type",
    "connection_type",
    "cross_section",
    "cross_section_unit",
    "cores"
]

class FingerprintBuilder:
    
    def build(self, record: UnifiedMaterialRecord) -> MaterialFingerprint:
        # 1. Gather technical identity in strict order
        identity = {}
        has_any_data = False
        
        for field in IDENTITY_FIELDS:
            # We strictly extract ONLY from the normalized properties that exist
            val = getattr(record, field, None)
            identity[field] = val
            if val is not None:
                has_any_data = True
                
        # 2. Serialize deterministically
        # We explicitly preserve None as null in JSON.
        # We prepend the schema version to ensure future schema changes alter the hash.
        raw_dict = {
            "version": FINGERPRINT_SCHEMA_VERSION,
            "identity": identity
        }
        
        # sort_keys=False because we already rely on our explicitly ordered python dict
        # Actually, python dict order is guaranteed (since 3.7), but sort_keys=True
        # is even safer to guarantee determinism in json.dumps regardless of how 'identity' was built.
        # However, the spec says "Fingerprint serialization must use a fixed attribute order."
        # We will iterate our fixed list and build a string, or rely on Python dict insertion order.
        # Let's manually build a serialized string to be 100% immune to JSON serialization quirks.
        
        components = [f"version:{FINGERPRINT_SCHEMA_VERSION}"]
        for field in IDENTITY_FIELDS:
            val = identity[field]
            # explicitly serialize None as "null" to preserve missingness unambiguously
            str_val = "null" if val is None else str(val)
            components.append(f"{field}:{str_val}")
            
        canonical_serialization = "|".join(components)
        
        # 3. Hash
        hasher = hashlib.sha256()
        hasher.update(canonical_serialization.encode('utf-8'))
        fingerprint_id = hasher.hexdigest()
        
        # 4. Determine status
        status = "PARTIAL"
        
        if record.source_conflict:
            status = "CONFLICTED"
        elif getattr(record, 'ambiguities', None):
            status = "AMBIGUOUS"
        elif has_any_data:
            # Not conflicted or ambiguous. 
            # We don't demand every single field to be non-null to call it "COMPLETE",
            # but usually "COMPLETE" implies sufficient identifying information. 
            # Given the dataset sparsity, if it has a commodity and material, it's pretty solid.
            # But the prompt says "Do not reject it merely because optional technical attributes are missing."
            if identity.get("commodity_class") and identity.get("material"):
                status = "COMPLETE"
            else:
                status = "PARTIAL"
        else:
            status = "PARTIAL" # Or EMPTY
            
        return MaterialFingerprint(
            fingerprint_id=fingerprint_id,
            fingerprint_schema_version=FINGERPRINT_SCHEMA_VERSION,
            fingerprint_status=status,
            technical_identity=identity,
            canonical_serialization=canonical_serialization
        )
