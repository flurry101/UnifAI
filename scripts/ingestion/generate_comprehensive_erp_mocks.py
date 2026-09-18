#!/usr/bin/env python3
"""
Generate Comprehensive Enterprise ERP Datasets for unifAI
Simulates real SAP ECC / S4HANA (MARA/MAKT/MARC/MBEW), Oracle Fusion Cloud SCM,
and IBM Maximo Asset Management tables with authentic schema structures.
"""

import csv
import json
from pathlib import Path

# Common catalog of 60 standard industrial materials across 5 CPSE sectors
CATALOG = [
    # 1-10: Valves
    {"item_id": 1, "cat": "VALVE", "sub": "BALL", "size": '2"', "rating": "CL150", "spec": "ASTM A216 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 2, "cat": "VALVE", "sub": "BALL", "size": '3"', "rating": "CL150", "spec": "ASTM A216 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 3, "cat": "VALVE", "sub": "BALL", "size": '4"', "rating": "CL300", "spec": "ASTM A216 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 4, "cat": "VALVE", "sub": "GATE", "size": '2"', "rating": "CL150", "spec": "API 600 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 5, "cat": "VALVE", "sub": "GATE", "size": '4"', "rating": "CL150", "spec": "API 600 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 6, "cat": "VALVE", "sub": "GATE", "size": '6"', "rating": "CL300", "spec": "API 600 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 7, "cat": "VALVE", "sub": "GLOBE", "size": '2"', "rating": "CL150", "spec": "ASTM A216 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 8, "cat": "VALVE", "sub": "GLOBE", "size": '3"', "rating": "CL300", "spec": "ASTM A216 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 9, "cat": "VALVE", "sub": "CHECK", "size": '4"', "rating": "CL150", "spec": "BS 1868 WCB", "uom": ("EA", "Each", "NOS")},
    {"item_id": 10, "cat": "VALVE", "sub": "BUTTERFLY", "size": '6"', "rating": "PN16", "spec": "DI BODY EPDM LINED", "uom": ("EA", "Each", "NOS")},
    
    # 11-20: Pipes & Tubes
    {"item_id": 11, "cat": "PIPE", "sub": "SEAMLESS", "size": '2"', "sch": "SCH 40", "spec": "ASTM A106 GR B", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 12, "cat": "PIPE", "sub": "SEAMLESS", "size": '3"', "sch": "SCH 40", "spec": "ASTM A106 GR B", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 13, "cat": "PIPE", "sub": "SEAMLESS", "size": '4"', "sch": "SCH 40", "spec": "ASTM A106 GR B", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 14, "cat": "PIPE", "sub": "SEAMLESS", "size": '6"', "sch": "SCH 40", "spec": "ASTM A106 GR B", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 15, "cat": "PIPE", "sub": "SEAMLESS", "size": '8"', "sch": "SCH 80", "spec": "ASTM A106 GR B", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 16, "cat": "PIPE", "sub": "STAINLESS", "size": '2"', "sch": "SCH 40S", "spec": "ASTM A312 TP304L", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 17, "cat": "PIPE", "sub": "STAINLESS", "size": '4"', "sch": "SCH 40S", "spec": "ASTM A312 TP304L", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 18, "cat": "PIPE", "sub": "STAINLESS", "size": '2"', "sch": "SCH 40S", "spec": "ASTM A312 TP316L", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 19, "cat": "PIPE", "sub": "ERW", "size": '100MM', "sch": "HEAVY", "spec": "IS 1239 PART 1", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 20, "cat": "PIPE", "sub": "ERW", "size": '150MM', "sch": "HEAVY", "spec": "IS 3589 FE 410", "uom": ("MTR", "Meter", "MTR")},
    
    # 21-28: Flanges
    {"item_id": 21, "cat": "FLANGE", "sub": "WNRF", "size": '2"', "rating": "CL150", "spec": "ASTM A105 SCH 40", "uom": ("EA", "Each", "PC")},
    {"item_id": 22, "cat": "FLANGE", "sub": "WNRF", "size": '4"', "rating": "CL150", "spec": "ASTM A105 SCH 40", "uom": ("EA", "Each", "PC")},
    {"item_id": 23, "cat": "FLANGE", "sub": "WNRF", "size": '6"', "rating": "CL300", "spec": "ASTM A105 SCH 40", "uom": ("EA", "Each", "PC")},
    {"item_id": 24, "cat": "FLANGE", "sub": "SORF", "size": '2"', "rating": "CL150", "spec": "ASTM A105", "uom": ("EA", "Each", "PC")},
    {"item_id": 25, "cat": "FLANGE", "sub": "SORF", "size": '4"', "rating": "CL150", "spec": "ASTM A105", "uom": ("EA", "Each", "PC")},
    {"item_id": 26, "cat": "FLANGE", "sub": "BLIND", "size": '2"', "rating": "CL150", "spec": "ASTM A105 RF", "uom": ("EA", "Each", "PC")},
    {"item_id": 27, "cat": "FLANGE", "sub": "BLIND", "size": '4"', "rating": "CL150", "spec": "ASTM A105 RF", "uom": ("EA", "Each", "PC")},
    {"item_id": 28, "cat": "FLANGE", "sub": "WNRF", "size": '2"', "rating": "CL150", "spec": "ASTM A182 F316L", "uom": ("EA", "Each", "PC")},

    # 29-35: Fasteners & Gaskets
    {"item_id": 29, "cat": "FASTENER", "sub": "STUD BOLT", "size": "3/4IN X 100MM", "spec": "A193 B7 W/ 2 NUTS A194 2H", "uom": ("SET", "Set", "SET")},
    {"item_id": 30, "cat": "FASTENER", "sub": "STUD BOLT", "size": "7/8IN X 120MM", "spec": "A193 B7 W/ 2 NUTS A194 2H", "uom": ("SET", "Set", "SET")},
    {"item_id": 31, "cat": "FASTENER", "sub": "STUD BOLT", "size": "1IN X 150MM", "spec": "A193 B7 W/ 2 NUTS A194 2H", "uom": ("SET", "Set", "SET")},
    {"item_id": 32, "cat": "FASTENER", "sub": "HEX BOLT", "size": "M16 X 60MM", "spec": "IS 1363 CLASS 8.8 GALV", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 33, "cat": "GASKET", "sub": "SPIRAL WOUND", "size": '2"', "rating": "CL150", "spec": "SS316 / GRAPHITE ASME B16.20", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 34, "cat": "GASKET", "sub": "SPIRAL WOUND", "size": '4"', "rating": "CL150", "spec": "SS316 / GRAPHITE ASME B16.20", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 35, "cat": "GASKET", "sub": "SPIRAL WOUND", "size": '6"', "rating": "CL300", "spec": "SS316 / GRAPHITE ASME B16.20", "uom": ("NOS", "Each", "NOS")},

    # 36-43: Electrical Cables & Transformer Spares
    {"item_id": 36, "cat": "CABLE", "sub": "HT XLPE", "size": "3C X 240 SQMM", "voltage": "11KV", "spec": "AL ARMOURED IS 7098 P2", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 37, "cat": "CABLE", "sub": "HT XLPE", "size": "3C X 300 SQMM", "voltage": "11KV", "spec": "AL ARMOURED IS 7098 P2", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 38, "cat": "CABLE", "sub": "HT XLPE", "size": "3C X 300 SQMM", "voltage": "33KV", "spec": "AL ARMOURED IS 7098 P2", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 39, "cat": "CABLE", "sub": "LT XLPE", "size": "4C X 16 SQMM", "voltage": "1.1KV", "spec": "AL ARMOURED IS 7098 P1", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 40, "cat": "CABLE", "sub": "LT XLPE", "size": "4C X 25 SQMM", "voltage": "1.1KV", "spec": "AL ARMOURED IS 7098 P1", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 41, "cat": "CABLE", "sub": "LT XLPE", "size": "4C X 50 SQMM", "voltage": "1.1KV", "spec": "AL ARMOURED IS 7098 P1", "uom": ("MTR", "Meter", "MTR")},
    {"item_id": 42, "cat": "OIL", "sub": "TRANSFORMER", "spec": "UNINHIBITED MINERAL OIL IS 335", "uom": ("LTR", "Liter", "LTR")},
    {"item_id": 43, "cat": "ELECTRICAL", "sub": "SILICA GEL", "spec": "BLUE INDICATING BREATHER GRADE", "uom": ("KG", "Kilogram", "KG")},

    # 44-50: Rotating Equipment & Pumps
    {"item_id": 44, "cat": "PUMP", "sub": "CENTRIFUGAL", "spec": "50 M3/HR 60M HEAD 37KW MOTOR", "uom": ("NOS", "Each", "SET")},
    {"item_id": 45, "cat": "PUMP", "sub": "CENTRIFUGAL", "spec": "100 M3/HR 45M HEAD 45KW MOTOR", "uom": ("NOS", "Each", "SET")},
    {"item_id": 46, "cat": "PUMP", "sub": "SUBMERSIBLE", "spec": "DEWATERING 30 M3/HR 25M HEAD 7.5KW", "uom": ("NOS", "Each", "SET")},
    {"item_id": 47, "cat": "MOTOR", "sub": "INDUCTION", "spec": "37 KW 4-POLE 415V 50HZ IE3 B3 FOOT", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 48, "cat": "MOTOR", "sub": "INDUCTION", "spec": "75 KW 4-POLE 415V 50HZ IE3 B3 FOOT", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 49, "cat": "COUPLING", "sub": "FLEXIBLE", "spec": "PIN BUSH TYPE SIZE F80 WITH PIN & BUSH", "uom": ("SET", "Set", "SET")},
    {"item_id": 50, "cat": "MECHANICAL SEAL", "sub": "CARTRIDGE", "spec": "SINGLE BALANCED 50MM FOR WATER PUMP", "uom": ("NOS", "Each", "NOS")},

    # 51-55: Bearings
    {"item_id": 51, "cat": "BEARING", "sub": "BALL", "spec": "DEEP GROOVE 6312 2Z C3 CLEARANCE", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 52, "cat": "BEARING", "sub": "BALL", "spec": "DEEP GROOVE 6315 C3 CLEARANCE OPEN", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 53, "cat": "BEARING", "sub": "ROLLER", "spec": "SPHERICAL ROLLER 22220 EK/C3 TAPER BORE", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 54, "cat": "BEARING", "sub": "ROLLER", "spec": "SPHERICAL ROLLER 22316 CC/W33", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 55, "cat": "BEARING", "sub": "BALL", "spec": "DEEP GROOVE 6208 2RS SEALED", "uom": ("NOS", "Each", "NOS")},

    # 56-60: Bulk Material Handling & Conveyor Components
    {"item_id": 56, "cat": "BELT", "sub": "CONVEYOR", "spec": "EP 800/4 1200MM WIDE 4+2 GRADE M", "uom": ("MTR", "Meter", "M")},
    {"item_id": 57, "cat": "BELT", "sub": "CONVEYOR", "spec": "EP 1000/4 1400MM WIDE 5+2 GRADE HR", "uom": ("MTR", "Meter", "M")},
    {"item_id": 58, "cat": "ROLLER", "sub": "IDLER", "spec": "TROUGHING IDLER ROLLER DIA 127MM X 465MM", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 59, "cat": "PULLEY", "sub": "CONVEYOR", "spec": "HEAD DRIVE PULLEY 500MM DIA X 1400MM FACE RUBBER LAGGED", "uom": ("NOS", "Each", "NOS")},
    {"item_id": 60, "cat": "INSTRUMENT", "sub": "TRANSMITTER", "spec": "PRESSURE TRANSMITTER 4-20MA HART 0-10 BAR 1/2IN NPT", "uom": ("NOS", "Each", "NOS")},
]

def make_sap_description(item):
    cat = item["cat"]
    sub = item.get("sub", "")
    size = item.get("size", "")
    rating = item.get("rating", "")
    spec = item.get("spec", "")
    sch = item.get("sch", "")
    voltage = item.get("voltage", "")

    if cat == "VALVE":
        return f"VLV {sub} {size} {rating} RF CS FLGD {spec}"
    elif cat == "PIPE":
        return f"PIPE {sub} {size} {sch} {spec}"
    elif cat == "FLANGE":
        return f"FLG {sub} {size} {rating} {spec}"
    elif cat == "FASTENER":
        return f"STUD BOLT {size} {spec}"
    elif cat == "GASKET":
        return f"GSK SP WOUND {size} {rating} {spec}"
    elif cat == "CABLE":
        return f"CBL {sub} {size} {voltage} {spec}"
    elif cat == "OIL":
        return f"OIL TRANS {spec}"
    elif cat == "PUMP":
        return f"PUMP {sub} {spec}"
    elif cat == "MOTOR":
        return f"MOTOR {sub} {spec}"
    elif cat == "BEARING":
        return f"BRG {sub} {spec}"
    elif cat == "BELT":
        return f"CNV BELT {spec}"
    else:
        return f"{cat} {sub} {spec}"

def make_oracle_description(item):
    cat = item["cat"]
    sub = item.get("sub", "")
    size = item.get("size", "")
    rating = item.get("rating", "")
    spec = item.get("spec", "")
    sch = item.get("sch", "")
    voltage = item.get("voltage", "")

    if cat == "VALVE":
        return f"{sub} VALVE SIZE {size} RATING {rating} RAISED FACE BODY {spec}"
    elif cat == "PIPE":
        return f"{sub} STEEL PIPE NOMINAL SIZE {size} WALL {sch} SPECIFICATION {spec}"
    elif cat == "FLANGE":
        return f"{sub} FLANGE {size} RATING {rating} MATERIAL {spec}"
    elif cat == "FASTENER":
        return f"HEAVY HEX STUD BOLT {size} WITH DUAL HEAVY HEX NUTS {spec}"
    elif cat == "GASKET":
        return f"SPIRAL WOUND METALLIC GASKET {size} CLASS {rating} {spec}"
    elif cat == "CABLE":
        return f"{voltage} GRADE {sub} POWER CABLE {size} {spec}"
    elif cat == "OIL":
        return f"INSULATING MINERAL TRANSFORMER OIL {spec}"
    elif cat == "PUMP":
        return f"HORIZONTAL {sub} PUMP SET {spec}"
    elif cat == "MOTOR":
        return f"SQUIRREL CAGE {sub} MOTOR {spec}"
    elif cat == "BEARING":
        return f"PRECISION {sub} BEARING {spec}"
    elif cat == "BELT":
        return f"HEAVY DUTY INDUSTRIAL RUBBER {sub} {spec}"
    else:
        return f"{cat} {sub} INDUSTRIAL {spec}"

def make_maximo_description(item):
    cat = item["cat"]
    sub = item.get("sub", "")
    size = item.get("size", "")
    rating = item.get("rating", "")
    spec = item.get("spec", "")
    sch = item.get("sch", "")
    voltage = item.get("voltage", "")

    if cat == "VALVE":
        return f"VALVE, {sub}, {size}, {rating}, {spec}, FLANGED"
    elif cat == "PIPE":
        return f"PIPE, {sub}, {size}, {sch}, {spec}"
    elif cat == "FLANGE":
        return f"FLANGE, {sub}, {size}, {rating}, {spec}"
    elif cat == "FASTENER":
        return f"BOLT, STUD, {size}, {spec}"
    elif cat == "GASKET":
        return f"GASKET, {sub}, {size}, {rating}, {spec}"
    elif cat == "CABLE":
        return f"CABLE, {sub}, {size}, {voltage}, {spec}"
    elif cat == "OIL":
        return f"OIL, TRANSFORMER, {spec}"
    elif cat == "PUMP":
        return f"PUMP, {sub}, {spec}"
    elif cat == "MOTOR":
        return f"MOTOR, ELECTRIC, {sub}, {spec}"
    elif cat == "BEARING":
        return f"BEARING, {sub}, {spec}"
    elif cat == "BELT":
        return f"BELT, CONVEYOR, {spec}"
    else:
        return f"{cat}, {sub}, {spec}"

def main():
    root = Path(__file__).resolve().parent.parent.parent
    mock_dir = root / "data" / "erp_mocks"
    mock_dir.mkdir(parents=True, exist_ok=True)

    # 1. SAP ECC / S4HANA Export (MARA, MAKT, MARC, MBEW)
    # Authentic columns: MATNR, MAKTX, MEINS, BSTME, MATKL, MTART, WERKS, LGORT, BKLAS, VPRSV, VERPR, STPRS, EXTWG
    sap_file = mock_dir / "sap_ecc_mara_export.csv"
    with open(sap_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "MATNR", "MAKTX", "MEINS", "BSTME", "MATKL", "MTART", "WERKS", "LGORT", "BKLAS", "VPRSV", "VERPR", "STPRS", "EXTWG"
        ])
        for item in CATALOG:
            matnr = f"00000000{10045890 + item['item_id']}"
            desc = make_sap_description(item)
            uom = item["uom"][0]
            matkl = f"{item['cat'][:3]}-01"
            mtart = "ERSA" if item["cat"] in ["VALVE", "BEARING", "PUMP", "MOTOR", "BELT", "ROLLER"] else "ROH"
            werks = "1001" if item["item_id"] % 2 == 0 else "1002"
            lgort = "0001"
            bklas = "3040" if mtart == "ERSA" else "3000"
            vprsv = "V"
            verpr = round(item["item_id"] * 1250.50, 2)
            stprs = verpr
            extwg = ""
            writer.writerow([matnr, desc, uom, uom, matkl, mtart, werks, lgort, bklas, vprsv, verpr, stprs, extwg])

    print(f"[+] Wrote {len(CATALOG)} enterprise records to {sap_file}")

    # 2. Oracle Fusion Cloud SCM Export (EGP_SYSTEM_ITEMS_B / TL, MTL_PARAMETERS)
    # Authentic columns: ITEM_NUMBER, ITEM_DESCRIPTION, ORGANIZATION_CODE, PRIMARY_UOM_CODE, SECONDARY_UOM_CODE, ITEM_CLASS_NAME, ITEM_TYPE, ITEM_STATUS, UNIT_COST, GLOBAL_ATTRIBUTE1
    oracle_file = mock_dir / "oracle_fusion_export.csv"
    with open(oracle_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ITEM_NUMBER", "ITEM_DESCRIPTION", "ORGANIZATION_CODE", "PRIMARY_UOM_CODE", "SECONDARY_UOM_CODE",
            "ITEM_CLASS_NAME", "ITEM_TYPE", "ITEM_STATUS", "UNIT_COST", "GLOBAL_ATTRIBUTE1"
        ])
        for item in CATALOG:
            item_num = f"ITM-{882100 + item['item_id']}"
            desc = make_oracle_description(item)
            uom = item["uom"][1]
            org = "V1_REFINERY" if item["item_id"] % 2 == 0 else "M1_POWER_STATION"
            item_class = f"{item['cat']}_CLASS"
            item_type = "Purchased Item"
            status = "Active"
            cost = round(item["item_id"] * 1245.00, 2)
            cnmc_tag = ""
            writer.writerow([item_num, desc, org, uom, "", item_class, item_type, status, cost, cnmc_tag])

    print(f"[+] Wrote {len(CATALOG)} enterprise records to {oracle_file}")

    # 3. IBM Maximo Asset Management Export (ITEM & INVENTORY Tables)
    # Authentic columns: ITEMNUM, DESCRIPTION, ITEMSETID, ITEMTYPE, ORDERUNIT, ISSUEUNIT, COMMODITYGROUP, COMMODITY, STATUS, ROTATING, SITEID, LOCATION, CURBAL, UNITCOST, NATIONAL_ID
    maximo_file = mock_dir / "maximo_asset_export.csv"
    with open(maximo_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ITEMNUM", "DESCRIPTION", "ITEMSETID", "ITEMTYPE", "ORDERUNIT", "ISSUEUNIT", "COMMODITYGROUP",
            "COMMODITY", "STATUS", "ROTATING", "SITEID", "LOCATION", "CURBAL", "UNITCOST", "NATIONAL_ID"
        ])
        for item in CATALOG:
            itemnum = f"MX-{40910 + item['item_id']}"
            desc = make_maximo_description(item)
            uom = item["uom"][2]
            itemset = "SET1"
            itemtype = "ITEM"
            comm_grp = item["cat"]
            comm = item.get("sub", item["cat"])
            status = "ACTIVE"
            rotating = 1 if item["cat"] in ["PUMP", "MOTOR"] else 0
            site = "BHILAI_STEEL" if item["item_id"] % 2 == 0 else "SINGRAULI_PWR"
            loc = "CENTRAL_STORE"
            curbal = (item["item_id"] * 7) % 50 + 5
            unitcost = round(item["item_id"] * 1260.00, 2)
            national_id = ""
            writer.writerow([itemnum, desc, itemset, itemtype, uom, uom, comm_grp, comm, status, rotating, site, loc, curbal, unitcost, national_id])

    print(f"[+] Wrote {len(CATALOG)} enterprise records to {maximo_file}")

if __name__ == "__main__":
    main()

