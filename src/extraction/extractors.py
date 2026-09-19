import re
from collections import defaultdict

def build_metadata(value, source_text, method="REGEX", confidence="HIGH"):
    """Helper to build standard extraction metadata."""
    if value is None:
        return None
    return {
        "value": value,
        "source_text": source_text.strip(),
        "method": method,
        "confidence": confidence
    }

def extract_commodity(text):
    """Conservative commodity extraction."""
    match = re.search(r'\b(valve|pipe|cable|bolt|nut|gasket|flange|tube)\b', text, re.IGNORECASE)
    if match:
        return {"commodity_class": [build_metadata(match.group(1).upper(), match.group(0), "CONTROLLED_VOCABULARY", "HIGH")]}
    return {}

def extract_material(text):
    """Extract base material."""
    match = re.search(r'\b(carbon steel|stainless steel|cs|ss|alloy steel|cast iron|brass|copper|al|aluminum)\b', text, re.IGNORECASE)
    if match:
        val = match.group(1).upper()
        if val == "CS": val = "CARBON STEEL"
        if val == "SS": val = "STAINLESS STEEL"
        if val == "AL": val = "ALUMINUM"
        return {"material": [build_metadata(val, match.group(0), "CONTROLLED_VOCABULARY", "HIGH")]}
    return {}

def extract_standard_and_grade(text):
    """Extract standard and grade avoiding pressure class confusion."""
    results = defaultdict(list)
    
    # 1. Look for explicit ASTM standards
    for astm_match in re.finditer(r'\b(astm\s+)?(a\d{3}[a-z]?)\b', text, re.IGNORECASE):
        std_raw = astm_match.group(2).upper()
        standard = f"ASTM {std_raw}" if not std_raw.startswith("ASTM") else std_raw
        results['standard'].append(build_metadata(standard, astm_match.group(0), "REGEX", "HIGH"))
        
    # Grades often used with ASTM
    for grade_match in re.finditer(r'\b(wcb|wcc|wc6|wc9|cf8|cf8m|cf3|cf3m|tp304l|tp316l|f304l|f316l|lcb|lcc)\b', text, re.IGNORECASE):
        results['material_grade'].append(build_metadata(grade_match.group(1).upper(), grade_match.group(0), "REGEX", "HIGH"))
            
    # 2. Look for API standards
    for api_match in re.finditer(r'\b(api\s+\w+)\b', text, re.IGNORECASE):
        results['standard'].append(build_metadata(api_match.group(1).upper(), api_match.group(0), "REGEX", "HIGH"))
        
    return dict(results)

def extract_dimensions(text):
    """Extract nominal size, outer diameter, thickness, schedule."""
    results = defaultdict(list)
    
    for size_match in re.finditer(r'\b(\d+(\.\d+)?)\s*(in)\b', text, re.IGNORECASE):
        results['nominal_size'].append(build_metadata(size_match.group(1), size_match.group(0), "REGEX", "HIGH"))
        results['size_unit'].append(build_metadata("IN", size_match.group(0), "REGEX", "HIGH"))
        
    for mm_size_match in re.finditer(r'\b(\d+(\.\d+)?)\s*(mm)\b', text, re.IGNORECASE):
        results['nominal_size'].append(build_metadata(mm_size_match.group(1), mm_size_match.group(0), "REGEX", "HIGH"))
        results['size_unit'].append(build_metadata("MM", mm_size_match.group(0), "REGEX", "HIGH"))
            
    for sch_match in re.finditer(r'\b(sch\s*(\d+s?)|(\d+s))\b', text, re.IGNORECASE):
        val = sch_match.group(2) if sch_match.group(2) else sch_match.group(3)
        results['schedule'].append(build_metadata(val.upper(), sch_match.group(0), "REGEX", "HIGH"))
        
    for thk_match in re.finditer(r'\b(thk|thick|thickness)\s*:?\s*(?:up\s+to\s+)?(\d+(\.\d+)?)\s*(mm|in)?\b', text, re.IGNORECASE):
        val = float(thk_match.group(2))
        unit = thk_match.group(4).upper() if thk_match.group(4) else None
        results['thickness'].append(build_metadata(val, thk_match.group(0), "REGEX", "HIGH"))
        if unit:
            results['thickness_unit'].append(build_metadata(unit, thk_match.group(0), "REGEX", "HIGH"))
            
    for thk_match2 in re.finditer(r'\b(\d+(\.\d+)?)\s*(mm|in)\s*(thk|thick|thickness)\b', text, re.IGNORECASE):
        val = float(thk_match2.group(1))
        unit = thk_match2.group(3).upper()
        results['thickness'].append(build_metadata(val, thk_match2.group(0), "REGEX", "HIGH"))
        results['thickness_unit'].append(build_metadata(unit, thk_match2.group(0), "REGEX", "HIGH"))
            
    return dict(results)

def extract_pressure(text):
    """Extract pressure class safely distinguishing systems."""
    results = defaultdict(list)
    
    for class_match in re.finditer(r'\bclass\s*(125|150|250|300|400|600|800|900|1500|2500|4500)\b(?:#|lb)?', text, re.IGNORECASE):
        results['pressure_class'].append(build_metadata(class_match.group(1), class_match.group(0), "REGEX", "HIGH"))
        results['pressure_class_system'].append(build_metadata("CLASS", class_match.group(0), "REGEX", "HIGH"))
        
    for pn_match in re.finditer(r'\bpn\s*(6|10|16|25|40|64|100|160|250|320|400)\b', text, re.IGNORECASE):
        results['pressure_class'].append(build_metadata(pn_match.group(1), pn_match.group(0), "REGEX", "HIGH"))
        results['pressure_class_system'].append(build_metadata("PN", pn_match.group(0), "REGEX", "HIGH"))
        
    return dict(results)

def extract_electrical(text):
    """Extract voltage, cross_section, cores safely."""
    results = defaultdict(list)
    
    for volt_match in re.finditer(r'\b(\d+(\.\d+)?)\s*(kv|v)\b', text, re.IGNORECASE):
        results['voltage'].append(build_metadata(float(volt_match.group(1)), volt_match.group(0), "REGEX", "HIGH"))
        results['voltage_unit'].append(build_metadata(volt_match.group(3).upper(), volt_match.group(0), "REGEX", "HIGH"))
        
    for core_match in re.finditer(r'\b(\d+)\s*c\b', text, re.IGNORECASE):
        results['cores'].append(build_metadata(int(core_match.group(1)), core_match.group(0), "REGEX", "HIGH"))
        
    for cs_match in re.finditer(r'\b(\d+(\.\d+)?)\s*(sq\.?mm|sqmm|mm2)\b', text, re.IGNORECASE):
        results['cross_section'].append(build_metadata(float(cs_match.group(1)), cs_match.group(0), "REGEX", "HIGH"))
        results['cross_section_unit'].append(build_metadata("SQ.MM", cs_match.group(0), "REGEX", "HIGH"))
        
    return dict(results)

def extract_connections(text):
    """Extract face type, thread type."""
    results = defaultdict(list)
    
    for face_match in re.finditer(r'\b(rf|raised face|ff|flat face|rtj|ring type joint)\b', text, re.IGNORECASE):
        val = face_match.group(1).upper()
        if val == "RAISED FACE": val = "RF"
        elif val == "FLAT FACE": val = "FF"
        elif val == "RING TYPE JOINT": val = "RTJ"
        results['face_type'].append(build_metadata(val, face_match.group(0), "REGEX", "HIGH"))
        
    for conn_match in re.finditer(r'\b(npt|bsp|flanged|threaded|sw|bw)\b', text, re.IGNORECASE):
        results['connection_type'].append(build_metadata(conn_match.group(1).upper(), conn_match.group(0), "REGEX", "HIGH"))
        
    return dict(results)

def extract_manufacturer(text):
    """Extract manufacturer and MPN (basic heuristic)."""
    results = defaultdict(list)
    
    # E.g., MAKE: FISHER, MFG: FLOWSERVE
    mfg_match = re.search(r'\b(make|mfg|manufacturer)[\s:]+([A-Za-z0-9\-\.]+)\b', text, re.IGNORECASE)
    if mfg_match:
        results['manufacturer'].append(build_metadata(mfg_match.group(2).upper(), mfg_match.group(0), "REGEX", "HIGH"))
        
    # E.g., PART NO: 12345, PN: 9876X
    mpn_match = re.search(r'\b(part no|pn|mpn)[\s:]+([A-Za-z0-9\-\.]+)\b', text, re.IGNORECASE)
    if mpn_match:
        results['manufacturer_part_number'].append(build_metadata(mpn_match.group(2).upper(), mpn_match.group(0), "REGEX", "HIGH"))
        
    return dict(results)
