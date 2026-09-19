#!/usr/bin/env python3
"""
Parse and harmonize official BIS Excel exports from data/reference/bis/
Extracts 8,000+ official Indian Standards and cross-references them against
the verified mandatory QCO registry (data/reference/bis_mandatory_qco_master.csv).

Zero hardcoded placeholder dictionaries. Uses Python standard library (zipfile + xml.etree.ElementTree).
"""

import os
import re
import glob
import csv
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Set

SOURCE_MAP = {
    "mopng": "Ministry of Petroleum & Natural Gas (MoPNG)",
    "mosteel": "Ministry of Steel",
    "mopower": "Ministry of Power",
    "moheavyindustries": "Ministry of Heavy Industries",
    "mocoal": "Ministry of Coal",
    "modpiit": "Department for Promotion of Industry and Internal Trade (DPIIT)",
    "med": "Mechanical Engineering Department (MED)",
    "mtd": "Metallurgical Engineering Department (MTD)",
    "etd": "Electrotechnical Department (ETD)",
    "pcd": "Petroleum, Coal and Related Products Department (PCD)",
}


def load_mandatory_qco_lookup(qco_csv_path: str) -> Dict[str, Dict[str, Any]]:
    """Load real mandatory QCO records extracted from official BIS Scheme-I and Scheme-X."""
    lookup = {}
    if not os.path.exists(qco_csv_path):
        return lookup

    with open(qco_csv_path, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            base_is = row["base_is_number"]
            if base_is not in lookup:
                lookup[base_is] = {
                    "mandatory": True,
                    "qco_name": row.get("qco_notification", "").strip(),
                    "category": row.get("category", "").strip(),
                    "scheme": row.get("scheme", "").strip()
                }
    return lookup


def parse_xlsx(file_path: str) -> List[Dict[str, Any]]:
    """Parse Excel sheets (.xlsx) using zipfile + ElementTree without external libraries."""
    records = []
    source_name = os.path.basename(file_path).replace(".xlsx", "").lower()
    category_name = SOURCE_MAP.get(source_name, source_name)

    with zipfile.ZipFile(file_path, "r") as z:
        # 1. Load shared strings
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                texts = [t.text or "" for t in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")]
                shared_strings.append("".join(texts))

        # 2. Parse sheet1
        sheet_xml = z.read("xl/worksheets/sheet1.xml")
        root = ET.fromstring(sheet_xml)
        rows = root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row")
        if not rows:
            return records

        for row_idx, row in enumerate(rows):
            cells = []
            for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                val = ""
                if v is not None and v.text is not None:
                    raw_val = v.text
                    if c.attrib.get("t") == "s":
                        idx = int(raw_val)
                        val = shared_strings[idx] if idx < len(shared_strings) else raw_val
                    else:
                        val = raw_val
                cells.append(val.strip())

            if not cells:
                continue

            # Skip title banner row (row 0) and header row (row 1 or 'Sl#')
            if row_idx == 0 or (cells and cells[0] == "Sl#"):
                continue

            # Data rows: ['Sl#', 'Standard Number', 'Date of Publish', 'Title', 'Type of Standard', 'Degree of Equivalence']
            if len(cells) >= 4:
                std_num = cells[1] if len(cells) > 1 else ""
                date_pub = cells[2] if len(cells) > 2 else ""
                title = cells[3] if len(cells) > 3 else ""
                std_type = cells[4] if len(cells) > 4 else ""
                equiv = cells[5] if len(cells) > 5 else ""

                if not std_num or not title:
                    continue

                # Clean base IS number: e.g. "IS 1239 (Part 1):2026" -> "IS 1239"
                base_match = re.match(r"((?:IS|IS/IEC|IS/ISO)\s*\d+)", std_num)
                base_is = base_match.group(1).replace("  ", " ") if base_match else std_num.split(":")[0]

                records.append({
                    "standard_number": std_num,
                    "base_is_number": base_is,
                    "title": title,
                    "date_of_publish": date_pub,
                    "type_of_standard": std_type,
                    "degree_of_equivalence": equiv,
                    "source_category": category_name,
                    "source_file": source_name
                })

    return records


def main():
    base_dir = "data/reference/bis"
    qco_master_path = "data/reference/bis_mandatory_qco_master.csv"
    out_csv = "data/reference/bis_standards_master.csv"

    xlsx_files = sorted(glob.glob(os.path.join(base_dir, "*.xlsx")))
    print(f"[*] Found {len(xlsx_files)} official BIS Excel files in {base_dir}")

    # Load official QCO lookup from real Scheme-I and Scheme-X data
    qco_lookup = load_mandatory_qco_lookup(qco_master_path)
    print(f"[*] Loaded {len(qco_lookup)} mandatory QCO standard families from {qco_master_path}")

    all_standards: Dict[str, Dict[str, Any]] = {}

    for f in xlsx_files:
        records = parse_xlsx(f)
        print(f"  -> {os.path.basename(f)}: parsed {len(records)} standards")

        for r in records:
            std_num = r["standard_number"]
            base_is = r["base_is_number"]

            qco_info = qco_lookup.get(base_is, {
                "mandatory": False,
                "qco_name": "",
                "category": ""
            })

            if std_num not in all_standards:
                all_standards[std_num] = {
                    "standard_number": std_num,
                    "base_is_number": base_is,
                    "title": r["title"],
                    "date_of_publish": r["date_of_publish"],
                    "type_of_standard": r["type_of_standard"],
                    "degree_of_equivalence": r["degree_of_equivalence"],
                    "categories": set([r["source_category"]]),
                    "source_files": set([r["source_file"]]),
                    "is_qco_mandatory": qco_info["mandatory"],
                    "qco_name": qco_info.get("qco_name", "")[:120],
                    "qco_category": qco_info.get("category", "")[:80]
                }
            else:
                all_standards[std_num]["categories"].add(r["source_category"])
                all_standards[std_num]["source_files"].add(r["source_file"])
                if qco_info["mandatory"]:
                    all_standards[std_num]["is_qco_mandatory"] = True
                    if qco_info.get("qco_name"):
                        all_standards[std_num]["qco_name"] = qco_info["qco_name"][:120]
                    if qco_info.get("category"):
                        all_standards[std_num]["qco_category"] = qco_info["category"][:80]

    print(f"\n[+] Total unique Indian Standards harmonized: {len(all_standards)}")

    # Export clean master CSV
    with open(out_csv, "w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "standard_number", "base_is_number", "title", "date_of_publish",
            "type_of_standard", "degree_of_equivalence", "ministries_and_departments",
            "source_files", "is_qco_mandatory", "qco_name", "qco_category"
        ])
        for std in sorted(all_standards.values(), key=lambda x: x["standard_number"]):
            writer.writerow([
                std["standard_number"],
                std["base_is_number"],
                std["title"],
                std["date_of_publish"],
                std["type_of_standard"],
                std["degree_of_equivalence"],
                "; ".join(sorted(std["categories"])),
                "; ".join(sorted(std["source_files"])),
                std["is_qco_mandatory"],
                std["qco_name"],
                std["qco_category"]
            ])

    qco_count = sum(1 for s in all_standards.values() if s["is_qco_mandatory"])
    mopng_count = sum(1 for s in all_standards.values() if any("Petroleum" in c for c in s["categories"]))

    print(f"[+] Master BIS Standards CSV saved: {out_csv} ({os.path.getsize(out_csv)} bytes)")
    print(f"[+] Standards directly tagged for Ministry of Petroleum & Natural Gas: {mopng_count}")
    print(f"[+] Standards verified under active Mandatory Quality Control Orders (QCOs): {qco_count}")


if __name__ == "__main__":
    main()
