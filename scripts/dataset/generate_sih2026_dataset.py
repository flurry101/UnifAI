import os
import json
import random
import uuid
import datetime
import pandas as pd
from itertools import combinations

SEED = 202609
random.seed(SEED)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "synthetic")
os.makedirs(DATA_DIR, exist_ok=True)

# Domain patterns learned from real corpus
UOM_PATTERNS = {"EA": ["EA", "Nos.", "No", "No.", "PCS", "EACH", "Nos", "no"], "M": ["M", "MTR", "Meter", "m"], "SQ.MM": ["SQ.MM", "SQMM", "MM2"]}
ABBREV_PATTERNS = {"Carbon Steel": ["CS", "C.S."], "Stainless Steel": ["SS", "S.S."], "Gate Valve": ["GV", "GATE V/V", "Gate Vlv"], "Class 150": ["CL150", "150#", "Cl 150"]}

def generate_canonical_materials():
    # Expand to 50 materials across categories (Valve, Pipe, Bolt, Cable, Pump, Motor)
    canonicals = []
    
    # 1. VALVES
    for i in range(15):
        m = {"commodity_class": "Valve", "type": random.choice(["Gate Valve", "Globe Valve", "Ball Valve", "Check Valve"]), "material": random.choice(["Carbon Steel", "Stainless Steel", "Alloy Steel"]), "pressure_class": random.choice(["Class 150", "Class 300", "Class 600", "PN16"]), "nominal_size": random.choice(["DN50", "DN100", "DN150"]), "standard": "ASME B16.34", "canonical_uom": "EA"}
        canonicals.append(m)
        
    # 2. PIPES
    for i in range(15):
        m = {"commodity_class": "Pipe", "material": random.choice(["Carbon Steel", "Stainless Steel", "HDPE", "PVC"]), "grade": random.choice(["API 5L Gr B", "TP304", "TP316L", "PE100"]), "nominal_size": random.choice(["DN100", "DN50", "DN200"]), "schedule": random.choice(["SCH40", "SCH80", "SCH10S"]), "length": "6m", "standard": "API 5L", "canonical_uom": "M"}
        canonicals.append(m)
        
    # 3. BOLTS
    for i in range(10):
        m = {"commodity_class": "Bolt", "type": random.choice(["Hex Head", "Stud Bolt", "Anchor Bolt"]), "material": random.choice(["Carbon Steel", "Stainless Steel"]), "grade": random.choice(["8.8", "10.9", "B7"]), "diameter": random.choice(["M12", "M20", "1/2 inch"]), "thread": random.choice(["Coarse", "Fine", "UNC"]), "length": "50mm", "canonical_uom": "EA"}
        canonicals.append(m)
        
    # 4. CABLES
    for i in range(10):
        m = {"commodity_class": "Cable", "type": random.choice(["Power Cable", "Control Cable"]), "conductor": random.choice(["Copper", "Aluminium"]), "cores": random.choice(["4 Core", "3 Core", "12 Core"]), "cross_section": random.choice(["2.5", "1.5", "240"]), "cross_section_unit": "SQ.MM", "voltage": random.choice(["1.1 kV", "3.3 kV", "11 kV"]), "canonical_uom": "M"}
        canonicals.append(m)

    df_rows = []
    for i, spec in enumerate(canonicals):
        c_id = f"CAN-{i+1:03d}"
        
        desc_parts = [spec.get("type") or spec.get("commodity_class")]
        for k in ["material", "grade", "nominal_size", "pressure_class", "schedule", "cores", "cross_section", "cross_section_unit", "voltage"]:
            if k in spec:
                desc_parts.append(spec[k])
                
        canonical_desc = " ".join(desc_parts).upper()
        
        c = {
            "canonical_id": c_id,
            "commodity_class": spec["commodity_class"],
            "canonical_description": canonical_desc,
            "canonical_uom": spec["canonical_uom"],
            **spec
        }
        df_rows.append(c)
        
    df = pd.DataFrame(df_rows)
    df.to_csv(os.path.join(DATA_DIR, "canonical_material.csv"), index=False)
    return df

def generate_renderings(canonical_df):
    materials = []
    counterfactuals = []
    
    cpses = ["CPSE_01", "CPSE_02", "CPSE_03", "CPSE_04", "CPSE_05"]
    mat_counter = 1
    cf_counter = 1
    
    # Track mappings for ground truth
    ground_truth_map = {} # canonical_id -> list of material_ids

    for _, row in canonical_df.iterrows():
        c_id = row["canonical_id"]
        c_desc = row["canonical_description"]
        ground_truth_map[c_id] = []
        
        # Multiple renderings per canonical, sometimes multiple in SAME CPSE (duplicate)
        num_renderings = random.randint(3, 8)
        
        for r_idx in range(num_renderings):
            cpse = random.choice(cpses)
            mat_id = f"MAT-{mat_counter:04d}"
            mat_code = f"MAT-{random.randint(10000, 99999)}"
            
            # Apply linguistic mutation
            desc = c_desc
            if random.random() < 0.5:
                for k, v in ABBREV_PATTERNS.items():
                    if k.upper() in desc:
                        desc = desc.replace(k.upper(), random.choice(v))
            if random.random() < 0.3:
                # Missing attribute
                words = desc.split()
                if len(words) > 3:
                    desc = " ".join(words[:-1]) # drop last part
                    
            uom = random.choice(UOM_PATTERNS.get(row["canonical_uom"], [row["canonical_uom"]]))
            
            materials.append({
                "material_id": mat_id,
                "cpse_id": cpse,
                "canonical_id": c_id,
                "material_code": mat_code,
                "description_original": desc,
                "base_uom": uom,
                "source_system": "SAP_ECC" if random.random() < 0.5 else "SAP_S4HANA",
                "source_record_id": f"REC-{mat_counter}",
                "source_file": "synthetic_generator",
                "source_row": mat_counter,
                "ingestion_timestamp": datetime.datetime.now().isoformat(),
                "processing_version": "2.0",
                "source_type": "SYNTHETIC"
            })
            ground_truth_map[c_id].append({"material_id": mat_id, "cpse": cpse})
            
            # Generate exactly 1 Counterfactual (VARIANT_OF) for 20% of records
            if random.random() < 0.2:
                cf_mat_id = f"MAT-CF-{cf_counter:04d}"
                cf_mat_code = f"MAT-{random.randint(10000, 99999)}"
                
                # Pick exactly one attribute to mutate
                mutatable = ["pressure_class", "nominal_size", "grade", "schedule", "voltage"]
                mutated = False
                for attr in mutatable:
                    if pd.notna(row.get(attr)):
                        old_val = str(row[attr])
                        # Quick hardcoded mutation
                        new_val = old_val + "X"
                        if "150" in old_val: new_val = "Class 300"
                        elif "100" in old_val: new_val = "DN150"
                        elif "40" in old_val: new_val = "SCH80"
                        
                        cf_desc = c_desc.replace(old_val.upper(), new_val.upper())
                        if cf_desc != c_desc:
                            counterfactuals.append({
                                "pair_id": f"CF-PR-{cf_counter:04d}",
                                "canonical_id": c_id,
                                "material_id_original": mat_id,
                                "material_id_mutated": cf_mat_id,
                                "changed_attribute": attr,
                                "original_value": old_val,
                                "mutated_value": new_val,
                                "expected_relation": "VARIANT_OF",
                                "difficulty": "HARD"
                            })
                            materials.append({
                                "material_id": cf_mat_id,
                                "cpse_id": cpse,
                                "canonical_id": c_id + "_VARIANT", # Important: Not the same canonical ID
                                "material_code": cf_mat_code,
                                "description_original": cf_desc,
                                "base_uom": uom,
                                "source_system": "SAP_ECC",
                                "source_record_id": f"REC-CF-{cf_counter}",
                                "source_file": "synthetic_generator",
                                "source_row": mat_counter,
                                "ingestion_timestamp": datetime.datetime.now().isoformat(),
                                "processing_version": "2.0",
                                "source_type": "SYNTHETIC_MUTATION"
                            })
                            cf_counter += 1
                            mutated = True
                            break
                
            mat_counter += 1

    df_mat = pd.DataFrame(materials)
    df_mat.to_csv(os.path.join(DATA_DIR, "material_master.csv"), index=False)
    
    df_cf = pd.DataFrame(counterfactuals)
    if not df_cf.empty:
        df_cf.to_csv(os.path.join(DATA_DIR, "counterfactual_pairs.csv"), index=False)
        
    return df_mat, ground_truth_map

def generate_relationships(ground_truth_map, materials_df):
    relationships = []
    evidence = []
    pair_counter = 1
    
    # Extract CF pairs
    cfs = []
    if os.path.exists(os.path.join(DATA_DIR, "counterfactual_pairs.csv")):
        cfs = pd.read_csv(os.path.join(DATA_DIR, "counterfactual_pairs.csv")).to_dict('records')
        
    # Generate IDENTICAL / EQUIVALENT
    for c_id, mats in ground_truth_map.items():
        if len(mats) > 1:
            for a, b in combinations(mats, 2):
                if random.random() < 0.3: # Don't generate ALL combinations
                    rel = "IDENTICAL" if a['cpse'] == b['cpse'] else "EQUIVALENT"
                    p_id = f"PR-{pair_counter:04d}"
                    relationships.append({
                        "pair_id": p_id,
                        "material_id_a": a['material_id'],
                        "cpse_a": a['cpse'],
                        "material_id_b": b['material_id'],
                        "cpse_b": b['cpse'],
                        "relation_type": rel,
                        "decision_status": "APPROVED",
                        "conflict_attributes": "",
                        "conflict_tier": "none",
                        "difficulty": "NORMAL",
                        "source_type": "SYNTHETIC"
                    })
                    evidence.append({
                        "pair_id": p_id,
                        "evidence_type": "LEXICAL_MATCH",
                        "attribute_name": "description",
                        "expected_effect": "SUPPORTIVE"
                    })
                    pair_counter += 1
                    
    # Generate DISTINCT
    all_mats = [m for sublist in ground_truth_map.values() for m in sublist]
    for i in range(200): # Random pairs between different canonicals
        a = random.choice(all_mats)
        b = random.choice(all_mats)
        if a['material_id'] != b['material_id']: # Note: we just skip checking canonical here for simplicity assuming low collision
            p_id = f"PR-{pair_counter:04d}"
            relationships.append({
                "pair_id": p_id,
                "material_id_a": a['material_id'],
                "cpse_a": a['cpse'],
                "material_id_b": b['material_id'],
                "cpse_b": b['cpse'],
                "relation_type": "DISTINCT",
                "decision_status": "APPROVED",
                "conflict_attributes": "multiple",
                "conflict_tier": "severe",
                "difficulty": "NORMAL",
                "source_type": "SYNTHETIC"
            })
            pair_counter += 1
            
    # Inject CFs as VARIANT_OF
    for cf in cfs:
        # Get CPSE info
        a_cpse = materials_df[materials_df['material_id'] == cf['material_id_original']]['cpse_id'].iloc[0]
        b_cpse = materials_df[materials_df['material_id'] == cf['material_id_mutated']]['cpse_id'].iloc[0]
        
        relationships.append({
            "pair_id": cf['pair_id'],
            "material_id_a": cf['material_id_original'],
            "cpse_a": a_cpse,
            "material_id_b": cf['material_id_mutated'],
            "cpse_b": b_cpse,
            "relation_type": "VARIANT_OF",
            "decision_status": "APPROVED",
            "conflict_attributes": cf['changed_attribute'],
            "conflict_tier": "near_miss",
            "difficulty": "HARD",
            "source_type": "SYNTHETIC_MUTATION"
        })
        evidence.append({
            "pair_id": cf['pair_id'],
            "evidence_type": "TECHNICAL_CONFLICT",
            "attribute_name": cf['changed_attribute'],
            "expected_effect": "CONTRADICTORY"
        })
        
    pd.DataFrame(relationships).to_csv(os.path.join(DATA_DIR, "ground_truth_relationships.csv"), index=False)
    pd.DataFrame(evidence).to_csv(os.path.join(DATA_DIR, "pair_evidence.csv"), index=False)

if __name__ == "__main__":
    print("Generating Dataset V2 Canonical Materials...")
    c_df = generate_canonical_materials()
    print("Generating Renderings & Counterfactuals...")
    m_df, gt_map = generate_renderings(c_df)
    print("Generating Ground Truth Relationships & Evidence...")
    generate_relationships(gt_map, m_df)
    print(f"Generated successfully in {DATA_DIR}")
