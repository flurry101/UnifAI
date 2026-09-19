import pytest
from pydantic import ValidationError
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance

def get_valid_provenance():
    return Provenance(
        source_type="ERP",
        source_system="SAP_ECC",
        source_record_id="MAT-1001",
        source_file="sap_export.csv",
        source_row=12,
        ingestion_timestamp="2026-09-18T12:00:00Z",
        processing_version="v2.0"
    )

def test_valid_material_record():
    """Test 1: valid material record parsing."""
    record = UnifiedMaterialRecord(
        provenance=get_valid_provenance(),
        original_material_code="1001",
        cpse="ONGC",
        source_system="SAP_ECC",
        original_description="GATE VALVE, CS, 4 IN, CL150, RF, ASTM A216 WCB",
        material_type="ERSA",
        commodity_class="Valve",
        material="Carbon Steel",
        nominal_size="4",
        size_unit="IN",
        pressure_class="150",
        manufacturer="L&T",
        canonical_uom="EA"
    )
    assert record.original_description == "GATE VALVE, CS, 4 IN, CL150, RF, ASTM A216 WCB"
    assert record.nominal_size == "4"
    assert record.canonical_uom == "EA"

def test_missing_technical_attributes():
    """Test 2 & 6: missing technical attributes / nullable fields."""
    record = UnifiedMaterialRecord(
        provenance=get_valid_provenance(),
        original_description="GATE VALVE UNKNOWN SIZE"
    )
    # Technical attributes should be None
    assert record.nominal_size is None
    assert record.pressure_class is None
    assert record.voltage is None

def test_preserved_original_description():
    """Test 3: preserved original description."""
    messy_desc = "  valve,, 4   inch !! "
    record = UnifiedMaterialRecord(
        provenance=get_valid_provenance(),
        original_description=messy_desc
    )
    assert record.original_description == messy_desc

def test_provenance_preservation():
    """Test 4: provenance preservation."""
    prov = get_valid_provenance()
    record = UnifiedMaterialRecord(
        provenance=prov,
        original_description="test"
    )
    d = record.to_dict()
    # Provenance fields should be flattened or accessible
    assert d['source_system'] == "SAP_ECC"
    assert d['source_record_id'] == "MAT-1001"
    assert 'provenance' not in d  # because to_dict pops and flattens it

def test_numeric_fields():
    """Test 5: numeric fields."""
    record = UnifiedMaterialRecord(
        provenance=get_valid_provenance(),
        original_description="test",
        thickness="12.5", # Should parse to float
        cores="4"         # Should parse to int
    )
    assert record.thickness == 12.5
    assert record.cores == 4
    
    with pytest.raises(ValidationError):
        UnifiedMaterialRecord(
            provenance=get_valid_provenance(),
            original_description="test",
            thickness="NotANumber"
        )

def test_invalid_required_identity():
    """Test 7: invalid required identity (missing original_description)."""
    with pytest.raises(ValidationError):
        UnifiedMaterialRecord(
            provenance=get_valid_provenance()
        )

def test_no_ground_truth_leakage():
    """Test 8: no ground-truth leakage."""
    record = UnifiedMaterialRecord(
        provenance=get_valid_provenance(),
        original_description="test",
        # We pass extra fields to see if they are ignored/removed
        canonical_id="CAN-999",
        expected_relationship="IDENTICAL",
        model_score=0.99
    )
    
    d = record.model_dump()
    assert 'canonical_id' not in d
    assert 'expected_relationship' not in d
    assert 'model_score' not in d
    assert not hasattr(record, 'canonical_id')
