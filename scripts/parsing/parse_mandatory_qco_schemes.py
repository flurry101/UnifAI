#!/usr/bin/env python3
"""
Parses official BIS Scheme-I and Scheme-X HTML exports into a clean, comprehensive mandatory QCO database.
Cross-references against data/reference/bis_standards_master.csv to update all mandatory QCO flags automatically.
"""

import os
import re
import csv
from bs4 import BeautifulSoup
from typing import Dict, List, Any

def clean_text(text: str) -> str:
    if not text: return ""
    return re.sub(r"\s+", " ", text).strip()

def parse_schemes():
    scheme1_file = "docs/bis/Scheme – I (ISI Mark Scheme) - Bureau of Indian Standards.html"
    schemeX_file = "docs/bis/Scheme – X (Certification) - Bureau of Indian Standards.html"
    
    records = []
    seen_standards = set()

    # 1. Parse Scheme-I (ISI Mark)
    if os.path.exists(scheme1_file):
        with open(scheme1_file, "r", encoding="utf-8", errors="ignore") as fp:
            soup = BeautifulSoup(fp.read(), "html.parser")
            for table in soup.find_all("table"):
                current_category = "General"
                current_qco = ""
                for r in table.find_all("tr"):
                    tds = [clean_text(td.get_text(" ", strip=True)) for td in r.find_all(["td", "th"])]
                    if not tds: continue
                    
                    # Category banner row
                    if len(tds) == 1 and not tds[0].startswith("Sr"):
                        current_category = tds[0]
                        continue
                    if "IS No." in tds: continue
                    
                    if len(tds) >= 3:
                        is_raw = tds[1]
                        product = tds[2]
                        qco_note = tds[3] if len(tds) > 3 else ""
                        if qco_note: current_qco = qco_note

                        # Multiple IS numbers might be comma or newline separated
                        is_tokens = re.findall(r"(?:IS|IS/IEC|IS/ISO)\s*[\d\(\)\s:/\-]+", is_raw)
                        if not is_tokens and is_raw.startswith("IS"):
                            is_tokens = [is_raw]

                        for is_token in is_tokens:
                            clean_is = clean_text(is_token)
                            if not clean_is: continue
                            base_match = re.match(r"((?:IS|IS/IEC|IS/ISO)\s*\d+)", clean_is)
                            base_is = base_match.group(1).replace("  ", " ") if base_match else clean_is.split(":")[0]

                            key = (clean_is, product)
                            if key not in seen_standards:
                                seen_standards.add(key)
                                records.append({
                                    "scheme": "Scheme-I (ISI Mark)",
                                    "standard_number": clean_is,
                                    "base_is_number": base_is,
                                    "product_name": product,
                                    "category": current_category,
                                    "qco_notification": current_qco
                                })

    # 2. Parse Scheme-X (Machinery and Electrical Equipment)
    if os.path.exists(schemeX_file):
        with open(schemeX_file, "r", encoding="utf-8", errors="ignore") as fp:
            soup = BeautifulSoup(fp.read(), "html.parser")
            for table in soup.find_all("table"):
                for r in table.find_all("tr"):
                    tds = [clean_text(td.get_text(" ", strip=True)) for td in r.find_all(["td", "th"])]
                    if len(tds) >= 3 and not tds[0].startswith("Sr"):
                        is_raw = tds[1]
                        product = tds[2]
                        details = tds[3] if len(tds) > 3 else ""
                        
                        is_tokens = re.findall(r"(?:IS|IS/IEC|IS/ISO)\s*[\d\(\)\s:/\-]+", is_raw)
                        if not is_tokens and ("IS" in is_raw):
                            is_tokens = [is_raw]

                        for is_token in is_tokens:
                            clean_is = clean_text(is_token)
                            base_match = re.match(r"((?:IS|IS/IEC|IS/ISO)\s*\d+)", clean_is)
                            base_is = base_match.group(1).replace("  ", " ") if base_match else clean_is.split(":")[0]

                            key = (clean_is, product)
                            if key not in seen_standards:
                                seen_standards.add(key)
                                records.append({
                                    "scheme": "Scheme-X (Machinery & Electrical)",
                                    "standard_number": clean_is,
                                    "base_is_number": base_is,
                                    "product_name": product,
                                    "category": "Machinery & Heavy Electrical Equipment",
                                    "qco_notification": "Machinery and Electrical Equipment Safety (Omnibus Technical Regulation) Order, 2024 / 2025"
                                })

    print(f"[+] Total mandatory items extracted from Scheme-I & Scheme-X: {len(records)}")

    # Write mandatory master CSV
    out_csv = "data/reference/bis_mandatory_qco_master.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["scheme", "standard_number", "base_is_number", "product_name", "category", "qco_notification"])
        writer.writeheader()
        writer.writerows(records)
    print(f"[+] Saved {out_csv} ({os.path.getsize(out_csv)} bytes)")

    # 3. Update bis_standards_master.csv with the real QCO mandatory flags
    standards_csv = "data/reference/bis_standards_master.csv"
    if os.path.exists(standards_csv):
        # Create fast lookup by base_is_number
        qco_lookup = {}
        for r in records:
            base = r["base_is_number"]
            qco_lookup[base] = r

        updated_rows = []
        mandatory_count = 0
        with open(standards_csv, "r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            fieldnames = reader.fieldnames
            for row in reader:
                base = row["base_is_number"]
                if base in qco_lookup:
                    row["is_qco_mandatory"] = "True"
                    match = qco_lookup[base]
                    row["qco_name"] = match["qco_notification"][:120] if match["qco_notification"] else match["scheme"]
                    row["qco_ministry"] = match["category"][:80]
                    mandatory_count += 1
                updated_rows.append(row)

        with open(standards_csv, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        print(f"[+] Successfully updated {standards_csv}: {mandatory_count} standards flagged as MANDATORY QCO from real BIS gazette orders!")

if __name__ == "__main__":
    parse_schemes()

