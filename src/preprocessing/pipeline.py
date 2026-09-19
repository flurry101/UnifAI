import os
import re
import csv

class PreprocessingPipeline:
    def __init__(self):
        # Load reference data
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.abbrev_path = os.path.join(base_dir, "data", "reference", "material_abbreviations.csv")
        self.uom_path = os.path.join(base_dir, "data", "reference", "unit_normalisation.csv")
        
        self.abbreviations = {}
        self.unit_mappings = {}
        
        self._load_abbreviations()
        self._load_uoms()
        
    def _load_abbreviations(self):
        if not os.path.exists(self.abbrev_path):
            # Fallback if running from a different working directory
            return
            
        with open(self.abbrev_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sf = row.get('surface_form', '').strip().lower()
                cf = row.get('canonical_form', '').strip().lower()
                if sf and cf:
                    self.abbreviations[sf] = cf

    def _load_uoms(self):
        if not os.path.exists(self.uom_path):
            return
            
        with open(self.uom_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sf = row.get('surface_form', '').strip().lower()
                cu = row.get('canonical_unit', '').strip().upper()  # UOM canonicals usually upper
                if sf and cu:
                    self.unit_mappings[sf] = cu

    def normalize_text(self, description: str) -> str:
        """
        Lane 2: Deterministic text normalization.
        """
        if not isinstance(description, str) or not description.strip():
            return ""
            
        # 1. Casing
        d = description.lower()
        
        # 2. Safe punctuation (keep hyphens, decimals, quotes for inches)
        # Pad commas and semicolons with spaces
        d = re.sub(r'([,;])', r' \1 ', d)
        
        # 3. Technical expression standardization
        # Standardize inch notations
        d = re.sub(r'\b(\d+(\.\d+)?)\s*(inch\b|in\b|")', r'\1 in', d)
        
        # Standardize classes
        d = re.sub(r'\b(class|cl)\s*(\d+)\b', r'class \2', d)
        d = re.sub(r'\b(\d+)\s*#', r'class \1', d)
        d = re.sub(r'\b(pn)\s*(\d+)\b', r'pn \2', d)
        
        # Standardize schedules
        d = re.sub(r'\b(schedule|sch)\s*(\d+s?)\b', r'sch \2', d)
        
        # Standardize voltages
        d = re.sub(r'\b(\d+(\.\d+)?)\s*kv\b', r'\1 kv', d)
        d = re.sub(r'\b(\d+(\.\d+)?)\s*v\b', r'\1 v', d)
        
        # 4. Tokenization for abbreviation replacement
        tokens = d.split()
        normalized_tokens = []
        for token in tokens:
            # Strip trailing punctuation from token temporarily to check abbreviation
            clean_token = token.strip(',;')
            if clean_token in self.abbreviations:
                # Replace with abbreviation, preserving any trailing punctuation we stripped
                replacement = self.abbreviations[clean_token]
                if token.endswith(',') or token.endswith(';'):
                    replacement += token[-1]
                normalized_tokens.append(replacement)
            else:
                normalized_tokens.append(token)
                
        d = ' '.join(normalized_tokens)
        
        # 5. Remove multiple spaces
        d = re.sub(r'\s+', ' ', d).strip()
        
        return d

    def normalize_uom(self, uom: str) -> str:
        if not isinstance(uom, str) or not uom.strip():
            return ""
        uom_lower = uom.strip().lower()
        return self.unit_mappings.get(uom_lower, uom_lower.upper())
        
    def process_record(self, record):
        if not getattr(record, 'original_description', None): 
            return record
            
        # Lane 2: Deterministic Normalization
        # original_description is PRESERVED exactly as it was.
        record.normalized_description = self.normalize_text(record.original_description)
        
        # UOM normalization (Lane 2)
        if record.canonical_uom:
            record.canonical_uom = self.normalize_uom(record.canonical_uom)
            
        return record
