import re

class PreprocessingPipeline:
    def __init__(self):
        # Basic mapping to test the unified pipeline
        self.abbreviations = {
            "C.S.": "CS", "S.S.": "SS", "SQMM": "SQ.MM", "MM2": "SQ.MM", "VLV": "VALVE"
        }
    
    def normalize(self, description: str) -> str:
        if not isinstance(description, str): return ""
        d = description.upper()
        # Abbreviation expansion
        for k, v in self.abbreviations.items():
            d = d.replace(k, v)
        # Punctuation spacing
        d = re.sub(r'([,;\-\/])', r' \1 ', d)
        # Remove multiple spaces
        d = re.sub(r'\s+', ' ', d).strip()
        return d
    
    def extract_attributes(self, norm_desc: str) -> dict:
        attrs = {}
        # Simple regex extraction for demonstration
        # Valve sizes
        m_size = re.search(r'\b(DN\s*\d+|\d+\s*MM|\d+\s*(INCH|IN|"))\b', norm_desc)
        if m_size: attrs['nominal_size'] = m_size.group(1).replace(" ", "")
        
        # Pressure class
        m_press = re.search(r'\b(CLASS\s*\d+|CL\s*\d+|\d+\s*#|PN\s*\d+)\b', norm_desc)
        if m_press: attrs['pressure_class'] = m_press.group(1).replace(" ", "")
        
        # Cable cross section
        m_cs = re.search(r'\b(\d+(\.\d+)?)\s*(SQ\.MM|SQMM|MM2)\b', norm_desc)
        if m_cs: 
            attrs['cross_section'] = m_cs.group(1)
            attrs['cross_section_unit'] = "SQ.MM"
            
        # Material
        if " CS " in norm_desc or "CARBON STEEL" in norm_desc: attrs['material'] = "Carbon Steel"
        if " SS " in norm_desc or "STAINLESS STEEL" in norm_desc: attrs['material'] = "Stainless Steel"
        
        # Commodity class hint
        if "VALVE" in norm_desc: attrs['commodity_class'] = "Valve"
        elif "PIPE" in norm_desc or " TUBE " in norm_desc: attrs['commodity_class'] = "Pipe"
        elif "CABLE" in norm_desc or "WIRE" in norm_desc: attrs['commodity_class'] = "Cable"
        elif "BOLT" in norm_desc or "NUT" in norm_desc: attrs['commodity_class'] = "Bolt"
            
        return attrs

    def process_record(self, record):
        if not record.description_original: return record
        record.description_normalized = self.normalize(record.description_original)
        attrs = self.extract_attributes(record.description_normalized)
        
        for k, v in attrs.items():
            setattr(record, k, v)
            
        return record
