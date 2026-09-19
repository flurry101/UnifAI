import pytest
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance
from src.fingerprint.builder import FingerprintBuilder

@pytest.fixture
def builder():
    return FingerprintBuilder()

def get_prov(cpse="CPSE_A", row=1):
    return Provenance(
        source_type="TEST",
        source_system="SYS",
        source_record_id=f"REC-{row}",
        source_file="f.csv",
        source_row=row,
        ingestion_timestamp="now",
        processing_version="v3"
    )

def test_fingerprint_deterministic_repeated(builder):
    record = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description="GATE VALVE",
        commodity_class="VALVE",
        material="CARBON STEEL"
    )
    fp1 = builder.build(record)
    fp2 = builder.build(record)
    assert fp1.fingerprint_id == fp2.fingerprint_id
    assert fp1.canonical_serialization == fp2.canonical_serialization

def test_same_identity_same_fingerprint(builder):
    # Two identical technical records from different CPSEs
    r1 = UnifiedMaterialRecord(
        provenance=get_prov(cpse="ONGC", row=10),
        original_description="GATE VALVE",
        commodity_class="VALVE",
        manufacturer="MFR A",
        manufacturer_part_number="123"
    )
    r2 = UnifiedMaterialRecord(
        provenance=get_prov(cpse="NTPC", row=99),
        original_description="GATE VALVE",
        commodity_class="VALVE",
        manufacturer="MFR B",
        manufacturer_part_number="XYZ"
    )
    fp1 = builder.build(r1)
    fp2 = builder.build(r2)
    assert fp1.fingerprint_id == fp2.fingerprint_id
    assert fp1.fingerprint_status == "PARTIAL"

def test_different_pressure_class_different_fingerprint(builder):
    r1 = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description="VALVE CL150",
        commodity_class="VALVE",
        pressure_class="150"
    )
    r2 = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description="VALVE CL300",
        commodity_class="VALVE",
        pressure_class="300"
    )
    fp1 = builder.build(r1)
    fp2 = builder.build(r2)
    assert fp1.fingerprint_id != fp2.fingerprint_id

def test_different_size_different_fingerprint(builder):
    r1 = UnifiedMaterialRecord(
        provenance=get_prov(), original_description="4 IN", nominal_size="4"
    )
    r2 = UnifiedMaterialRecord(
        provenance=get_prov(), original_description="6 IN", nominal_size="6"
    )
    assert builder.build(r1).fingerprint_id != builder.build(r2).fingerprint_id

def test_different_grade_different_fingerprint(builder):
    r1 = UnifiedMaterialRecord(
        provenance=get_prov(), original_description="WCB", material_grade="WCB"
    )
    r2 = UnifiedMaterialRecord(
        provenance=get_prov(), original_description="LCC", material_grade="LCC"
    )
    assert builder.build(r1).fingerprint_id != builder.build(r2).fingerprint_id

def test_missing_attribute_preserved(builder):
    r = UnifiedMaterialRecord(
        provenance=get_prov(), original_description="VALVE", commodity_class="VALVE"
    )
    fp = builder.build(r)
    assert "material:null" in fp.canonical_serialization
    assert "commodity_class:VALVE" in fp.canonical_serialization

def test_ambiguity_preserved(builder):
    r = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description="VALVE",
        commodity_class="VALVE",
        ambiguities={"pressure_class": {"type": "MULTIPLE_EXTRACTIONS", "values": ["150", "300"]}}
    )
    fp = builder.build(r)
    # Ambiguity makes status AMBIGUOUS
    assert fp.fingerprint_status == "AMBIGUOUS"
    # But fingerprint remains deterministic over the base fields
    assert "pressure_class:null" in fp.canonical_serialization

def test_conflict_preserved(builder):
    r = UnifiedMaterialRecord(
        provenance=get_prov(),
        original_description="VALVE",
        commodity_class="VALVE",
        source_conflict=True
    )
    fp = builder.build(r)
    assert fp.fingerprint_status == "CONFLICTED"

def test_fingerprint_schema_version_included(builder):
    r = UnifiedMaterialRecord(
        provenance=get_prov(), original_description="VALVE"
    )
    fp = builder.build(r)
    assert fp.canonical_serialization.startswith("version:v1|")
