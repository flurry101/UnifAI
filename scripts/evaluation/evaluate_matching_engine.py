#!/usr/bin/env python3
"""
Evaluation script for CPSE Material Standardization and Harmonization Engine.
Tests normalization, attribute parsing, engineering compatibility gates,
hybrid scoring, and graph clustering on ground truth benchmarks.
"""

import csv
import re
from typing import Dict, Any, List, Tuple, Set

class MaterialNormalizer:
    def __init__(self, abbr_path: str, grades_path: str, pressure_path: str, units_path: str):
        self.abbreviations = {}
        with open(abbr_path, mode='r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                self.abbreviations[row['surface_form'].upper()] = row['canonical_form'].upper()

        self.grades = {}
        with open(grades_path, mode='r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                self.grades[row['grade_token'].upper()] = row['grade'].upper()

        self.pressure_classes = {}
        with open(pressure_path, mode='r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                self.pressure_classes[row['surface_form'].upper()] = row['asme_class'].upper()

        self.units = {}
        with open(units_path, mode='r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                self.units[row['surface_form'].upper()] = row['canonical_unit'].upper()

    def normalize_text(self, text: str) -> str:
        # Standardize whitespace and punctuation
        t = re.sub(r'[\*,;:]+', ' ', text.upper())
        tokens = t.split()
        expanded = []
        for tok in tokens:
            expanded.append(self.abbreviations.get(tok, tok))
        return ' '.join(expanded)

    def extract_attributes(self, text: str) -> Dict[str, Any]:
        norm = self.normalize_text(text)
        attrs = {
            'normalized_text': norm,
            'grade': None,
            'pressure_rating': None,
            'size_dimension': None,
            'primary_category': None
        }
        
        # Check pressure class
        for p_surf, p_canon in self.pressure_classes.items():
            if re.search(r'\b' + re.escape(p_surf) + r'\b', norm):
                attrs['pressure_rating'] = p_canon
                break
                
        # Check material grade
        for g_tok, g_canon in self.grades.items():
            if re.search(r'\b' + re.escape(g_tok) + r'\b', norm):
                attrs['grade'] = g_canon
                break

        # Check size (e.g. M10, 2 IN, DN50, 150 NB, 6IN, 240 SQMM)
        size_match = re.search(r'\b(M\d+|DN\s*\d+|\d+\s*IN|\d+\s*INCH|\d+\s*NB|\d+\s*SQ\.?MM|\d+\s*MM)\b', norm)
        if size_match:
            attrs['size_dimension'] = size_match.group(1).replace(' ', '')

        return attrs

def compute_similarity(a_attrs: Dict[str, Any], b_attrs: Dict[str, Any], uom_a: str, uom_b: str) -> Tuple[float, str]:
    """
    Computes hybrid similarity with Engineering Safety Gates.
    Returns (score, rationale).
    """
    # Safety Gate 1: Metallurgical / Material Grade Incompatibility
    if a_attrs['grade'] and b_attrs['grade']:
        if a_attrs['grade'] != b_attrs['grade']:
            # Critical engineering conflict: cannot merge SS304 with Grade 8.8 or CS with SS
            return (0.0, f"CONFLICT_METALLURGY_MISMATCH: {a_attrs['grade']} != {b_attrs['grade']}")

    # Safety Gate 2: Pressure Rating Incompatibility
    if a_attrs['pressure_rating'] and b_attrs['pressure_rating']:
        if a_attrs['pressure_rating'] != b_attrs['pressure_rating']:
            return (0.0, f"CONFLICT_PRESSURE_MISMATCH: {a_attrs['pressure_rating']} != {b_attrs['pressure_rating']}")

    # Token overlap score for textual description
    tokens_a = set(a_attrs['normalized_text'].split())
    tokens_b = set(b_attrs['normalized_text'].split())
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    jaccard = len(intersection) / len(union) if union else 0.0

    # Size score
    size_score = 1.0 if a_attrs['size_dimension'] == b_attrs['size_dimension'] else 0.0
    if not a_attrs['size_dimension'] and not b_attrs['size_dimension']:
        size_score = 0.8

    # UoM compatibility
    uom_score = 1.0 if uom_a.strip().upper() == uom_b.strip().upper() else 0.5

    # Weighted composite score: Text 50% + Tech Spec 35% + UoM 15%
    composite = (0.50 * jaccard) + (0.35 * size_score) + (0.15 * uom_score)
    return (composite, "MATCH_COMPATIBLE")


def main():
    normalizer = MaterialNormalizer(
        abbr_path='data/reference/material_abbreviations.csv',
        grades_path='data/reference/material_grades.csv',
        pressure_path='data/reference/pressure_classes.csv',
        units_path='data/reference/unit_normalisation.csv'
    )

    benchmark_records = []
    with open('data/benchmark/cpse_cross_sector_groundtruth_benchmark.csv', mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            benchmark_records.append(r)

    print(f"Loaded {len(benchmark_records)} benchmark records.")
    
    # Pairwise evaluation
    tp, fp, tn, fn = 0, 0, 0, 0
    gate_triggers = 0
    threshold = 0.55

    for i in range(len(benchmark_records)):
        for j in range(i + 1, len(benchmark_records)):
            rec_a = benchmark_records[i]
            rec_b = benchmark_records[j]
            is_same_cluster = (rec_a['groundtruth_cluster_id'] == rec_b['groundtruth_cluster_id'])

            attrs_a = normalizer.extract_attributes(rec_a['raw_material_description'])
            attrs_b = normalizer.extract_attributes(rec_b['raw_material_description'])
            uom_a = normalizer.units.get(rec_a['unit_of_measure'].upper(), rec_a['unit_of_measure'])
            uom_b = normalizer.units.get(rec_b['unit_of_measure'].upper(), rec_b['unit_of_measure'])

            score, rationale = compute_similarity(attrs_a, attrs_b, uom_a, uom_b)
            if "CONFLICT" in rationale:
                gate_triggers += 1

            predicted_match = (score >= threshold)

            if predicted_match and is_same_cluster:
                tp += 1
            elif predicted_match and not is_same_cluster:
                fp += 1
            elif not predicted_match and not is_same_cluster:
                tn += 1
            elif not predicted_match and is_same_cluster:
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    print("================ EVALUATION RESULTS ================")
    print(f"Total Candidate Pairs Evaluated: {tp + fp + tn + fn}")
    print(f"True Positives (Identical/Equivalent Merged): {tp}")
    print(f"False Positives (Erroneous Merges): {fp}")
    print(f"True Negatives (Correctly Separated): {tn}")
    print(f"False Negatives (Missed Merges): {fn}")
    print(f"Engineering Safety Gate Rejections: {gate_triggers}")
    print(f"Precision: {precision:.4f} (Target: >0.90 for zero erroneous merges)")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print("=====================================================")

if __name__ == '__main__':
    main()

