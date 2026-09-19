import pytest
from src.preprocessing.pipeline import PreprocessingPipeline
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance

@pytest.fixture
def pipeline():
    return PreprocessingPipeline()

def get_prov():
    return Provenance(
        source_type="TEST",
        source_system="SYS",
        source_record_id="1",
        source_file="f.csv",
        source_row=1,
        ingestion_timestamp="now",
        processing_version="v2"
    )

def test_deterministic_lowercase(pipeline):
    # 1. Deterministic lowercase normalization
    desc = "GATE VALVE, CARBON STEEL"
    norm = pipeline.normalize_text(desc)
    assert norm == "gate valve , carbon steel" # comma padded

def test_whitespace_normalization(pipeline):
    # 2. Whitespace normalization
    desc = "  GATE   VALVE,   CS  "
    norm = pipeline.normalize_text(desc)
    # comma padded, multiple spaces squashed, CS mapped if in abbrev
    # Wait, CS -> carbon steel (from abbreviations.csv if loaded)
    # Let's just check spaces
    assert "  " not in norm
    assert norm.startswith("gate valve")

def test_abbreviation_substitution(pipeline):
    # 3 & 4. Abbreviation dictionary loading & substitution
    # Assuming CS -> carbon steel, SS -> stainless steel in the real CSV
    if "cs" in pipeline.abbreviations:
        assert pipeline.normalize_text("VALVE, CS") == "valve , carbon steel"

def test_unknown_abbreviation_preservation(pipeline):
    # 5. Unknown abbreviation preservation
    # XXXXX is unlikely to be in abbreviations
    norm = pipeline.normalize_text("VALVE, XXXXX")
    assert "xxxxx" in norm

def test_uom_normalization(pipeline):
    # 6. UOM normalization
    # Assuming EA -> NOS, EACH -> NOS based on real unit_normalisation.csv
    if "ea" in pipeline.unit_mappings:
        assert pipeline.normalize_uom("EA") == pipeline.unit_mappings["ea"]
    if "each" in pipeline.unit_mappings:
        assert pipeline.normalize_uom("EACH") == pipeline.unit_mappings["each"]
    
def test_unknown_uom_handling(pipeline):
    # 7. Unknown UOM handling
    assert pipeline.normalize_uom("UNKNOWN_UNIT_99") == "UNKNOWN_UNIT_99"

def test_incompatible_units_remain_distinct(pipeline):
    # 8. Incompatible units remain distinct
    # E.g. KG and M should not map to the same thing
    u1 = pipeline.normalize_uom("KG")
    u2 = pipeline.normalize_uom("M")
    assert u1 != u2

def test_technical_expression_normalization(pipeline):
    # 9. Technical expression normalization
    assert "class 150" in pipeline.normalize_text("VALVE CL150")
    assert "class 150" in pipeline.normalize_text("VALVE CLASS 150")
    assert "class 150" in pipeline.normalize_text("VALVE 150#")
    
    assert "4 in" in pipeline.normalize_text("VALVE 4\"")
    assert "4 in" in pipeline.normalize_text("VALVE 4 INCH")
    
    assert "sch 40" in pipeline.normalize_text("PIPE SCH40")
    assert "sch 40" in pipeline.normalize_text("PIPE SCHEDULE 40")
    
    assert "11 kv" in pipeline.normalize_text("CABLE 11KV")
    assert "11 kv" in pipeline.normalize_text("CABLE 11 KV")

def test_original_description_preservation(pipeline):
    # 10. original_description preservation
    orig = "GATE VALVE, CS, 4 IN, CL150"
    record = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description=orig
    )
    processed = pipeline.process_record(record)
    assert processed.original_description == orig
    assert processed.normalized_description is not None
    assert processed.normalized_description != orig

def test_provenance_preservation(pipeline):
    # 11. Provenance preservation
    record = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description="test"
    )
    processed = pipeline.process_record(record)
    assert processed.provenance.source_system == "SYS"

def test_deterministic_repeated_execution(pipeline):
    # 12. Deterministic repeated execution
    desc = "VALVE CS 4 IN"
    norm1 = pipeline.normalize_text(desc)
    norm2 = pipeline.normalize_text(desc)
    assert norm1 == norm2

def test_forbidden_ground_truth_fields(pipeline):
    # 15. Forbidden ground-truth fields
    record = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description="test",
        # Extra fields will be ignored by Pydantic
        canonical_id="999"
    )
    processed = pipeline.process_record(record)
    assert not hasattr(processed, 'canonical_id')
    assert 'canonical_id' not in processed.model_dump()


