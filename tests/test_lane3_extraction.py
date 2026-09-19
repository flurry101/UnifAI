import pytest
from src.preprocessing.pipeline import PreprocessingPipeline
from src.extraction.engine import ExtractionEngine
from src.ingestion.unified_schema import UnifiedMaterialRecord, Provenance

@pytest.fixture
def pipeline():
    return PreprocessingPipeline()

@pytest.fixture
def engine():
    return ExtractionEngine()

def get_prov():
    return Provenance(
        source_type="TEST",
        source_system="SYS",
        source_record_id="1",
        source_file="f.csv",
        source_row=1,
        ingestion_timestamp="now",
        processing_version="v3"
    )

def test_valve_extraction(pipeline, engine):
    orig = "GATE VALVE, CS, 4 IN, CL150, RF, ASTM A216 WCB"
    record = UnifiedMaterialRecord(provenance=get_prov(), original_description=orig)
    
    record = pipeline.process_record(record)
    record = engine.process(record)
    
    assert record.commodity_class == "VALVE"
    assert record.material == "CARBON STEEL"
    assert record.nominal_size == "4"
    assert record.size_unit == "IN"
    assert record.pressure_class == "150"
    assert record.pressure_class_system == "CLASS"
    assert record.face_type == "RF"
    assert record.standard == "ASTM A216"
    assert record.material_grade == "WCB"

def test_pipe_extraction(pipeline, engine):
    orig = "SEAMLESS, SS, A312-TP304L, 80S, 15MM, PIPE"
    record = UnifiedMaterialRecord(provenance=get_prov(), original_description=orig)
    
    record = pipeline.process_record(record)
    record = engine.process(record)
    
    assert record.commodity_class == "PIPE"
    assert record.material == "STAINLESS STEEL"
    assert record.standard == "ASTM A312"
    assert record.material_grade == "TP304L"
    assert record.schedule == "80S"
    assert record.nominal_size == "15"
    assert record.size_unit == "MM"

def test_cable_extraction(pipeline, engine):
    orig = "CABLE, PWR, 240MM2, 1C, STRANDED, AL, 11KV"
    record = UnifiedMaterialRecord(provenance=get_prov(), original_description=orig)
    
    record = pipeline.process_record(record)
    record = engine.process(record)
    
    assert record.commodity_class == "CABLE"
    assert record.material == "ALUMINUM"
    assert record.cross_section == 240.0
    assert record.cross_section_unit == "SQ.MM"
    assert record.cores == 1
    assert record.voltage == 11.0
    assert record.voltage_unit == "KV"

def test_counterfactual_technical_differences(pipeline, engine):
    # CL150 vs CL300
    r1 = pipeline.process_record(UnifiedMaterialRecord(provenance=get_prov(), original_description="VALVE CL150"))
    r2 = pipeline.process_record(UnifiedMaterialRecord(provenance=get_prov(), original_description="VALVE CL300"))
    r1 = engine.process(r1)
    r2 = engine.process(r2)
    assert r1.pressure_class == "150" and r2.pressure_class == "300"
    
    # SCH40 vs SCH80
    r1 = pipeline.process_record(UnifiedMaterialRecord(provenance=get_prov(), original_description="PIPE SCH40"))
    r2 = pipeline.process_record(UnifiedMaterialRecord(provenance=get_prov(), original_description="PIPE SCH80"))
    r1 = engine.process(r1)
    r2 = engine.process(r2)
    assert r1.schedule == "40" and r2.schedule == "80"
    
    # 11KV vs 33KV
    r1 = pipeline.process_record(UnifiedMaterialRecord(provenance=get_prov(), original_description="CABLE 11 KV"))
    r2 = pipeline.process_record(UnifiedMaterialRecord(provenance=get_prov(), original_description="CABLE 33 KV"))
    r1 = engine.process(r1)
    r2 = engine.process(r2)
    assert r1.voltage == 11.0 and r2.voltage == 33.0

def test_unknown_vocabulary_preservation(pipeline, engine):
    orig = "VALVE XYZ999 4 IN"
    record = UnifiedMaterialRecord(provenance=get_prov(), original_description=orig)
    
    record = pipeline.process_record(record)
    record = engine.process(record)
    
    assert record.original_description == orig
    assert record.nominal_size == "4"
    assert "xyz999" in record.normalized_description
    assert not hasattr(record, 'xyz999') # No hallucination

def test_source_conflict_detection(pipeline, engine):
    # Structured = 150, text says CLASS 300
    record = UnifiedMaterialRecord(
        provenance=get_prov(), 
        original_description="VALVE CLASS 300",
        pressure_class="150"
    )
    
    record = pipeline.process_record(record)
    record = engine.process(record)
    
    assert record.pressure_class == "150" # Existing not overwritten
    assert record.source_conflict is True
    assert "pressure_class" in record.source_conflicts
    assert record.source_conflicts["pressure_class"]["extracted_value"] == "300"
    assert record.source_conflicts["pressure_class"]["extracted_text"] == "class 300"
    
def test_multiple_match_ambiguity(pipeline, engine):
    # Text says both CLASS 150 and CLASS 300
    record = UnifiedMaterialRecord(
        provenance=get_prov(), 
        original_description="VALVE CLASS 150 / CLASS 300"
    )
    
    record = pipeline.process_record(record)
    record = engine.process(record)
    
    assert record.pressure_class is None # Not blindly guessing which one
    assert record.source_conflict is False # Ambiguity is not a source conflict unless it contradicts structured data
    assert "pressure_class" in record.ambiguities
    assert record.ambiguities["pressure_class"]["type"] == "MULTIPLE_EXTRACTIONS"
    assert "150" in record.ambiguities["pressure_class"]["values"]
    assert "300" in record.ambiguities["pressure_class"]["values"]
