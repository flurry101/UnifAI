import re

def extract_dimension(text: str) -> str | None:
    """
    Extracts and normalizes dimensions (e.g., '4 IN', 'DN100', '100 MM').
    """
    # Look for patterns like: 4", 4 IN, 4 INCH, DN100, DN 100, 100 MM, 100MM
    text = text.upper()
    
    # 1. DN matches (e.g., DN100, DN 100)
    dn_match = re.search(r'\bDN\s*(\d+)\b', text)
    if dn_match:
        return f"DN{dn_match.group(1)}"
        
    # 2. INCH matches (e.g., 4 IN, 4 INCH, 4", 4.5 IN)
    inch_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:IN|INCH|")\b', text.replace('"', ' " '))
    if inch_match:
        return f"{inch_match.group(1)} INCH"
        
    # 3. MM matches (e.g., 100 MM, 100MM)
    mm_match = re.search(r'\b(\d+(?:\.\d+)?)\s*MM\b', text)
    if mm_match:
        return f"{mm_match.group(1)} MM"
        
    return None


def extract_pressure(text: str) -> str | None:
    """
    Extracts and normalizes pressure classes (e.g., 'CL150', '150#', 'CLASS 150', 'PN16').
    """
    text = text.upper()
    
    # 1. Class matches (e.g., CL150, 150#, CLASS 150)
    class_match = re.search(r'\b(?:CL|CLASS)\s*(\d+)\b', text)
    if class_match:
        return f"{class_match.group(1)}"
        
    hash_match = re.search(r'\b(\d+)#', text)
    if hash_match:
        return f"{hash_match.group(1)}"
        
    # 2. PN matches (e.g., PN16, PN 16)
    pn_match = re.search(r'\bPN\s*(\d+)\b', text)
    if pn_match:
        return f"PN{pn_match.group(1)}"
        
    return None


def extract_material_grade(text: str) -> str | None:
    """
    Extracts and normalizes material grades.
    """
    text = text.upper()
    
    if re.search(r'\b(316L|SS\s*316L)\b', text):
        return "316L"
    if re.search(r'\b(SS316|316|SS\s*316)\b', text):
        return "SS316"
    if re.search(r'\b(304L|SS\s*304L)\b', text):
        return "304L"
    if re.search(r'\b(SS304|304|SS\s*304)\b', text):
        return "SS304"
    if re.search(r'\b(CS|CARBON STEEL)\b', text):
        return "CARBON STEEL"
    if re.search(r'\b(WCB|A216\s*WCB|A216-WCB)\b', text):
        return "WCB"
    if re.search(r'\b(A105)\b', text):
        return "A105"
        
    return None


def extract_standard(text: str) -> str | None:
    """
    Extracts and normalizes standards like ASTM A216, ASME B16.5
    """
    text = text.upper()
    
    std_match = re.search(r'\b(ASTM\s+[A-Z0-9]+|ASME\s+[A-Z0-9\.]+|API\s+\d+|IS\s+\d+)\b', text)
    if std_match:
        return std_match.group(1).replace(" ", "")  # Normalize spaces (e.g., ASTMA216)
        
    return None


def detect_technical_conflict(query_desc: str, cand_desc: str) -> bool:
    """
    Detects base component type conflicts (e.g. GATE vs GLOBE).
    """
    query_desc = query_desc.upper()
    cand_desc = cand_desc.upper()
    
    components = [
        "GATE VALVE", "GLOBE VALVE", "BALL VALVE", "CHECK VALVE", "BUTTERFLY VALVE",
        "PIPE", "FLANGE", "FITTING", "PUMP", "MOTOR", "ACTUATOR"
    ]
    
    q_comp = None
    for comp in components:
        if comp in query_desc:
            q_comp = comp
            break
            
    c_comp = None
    for comp in components:
        if comp in cand_desc:
            c_comp = comp
            break
            
    if q_comp and c_comp and q_comp != c_comp:
        return True
        
    return False
