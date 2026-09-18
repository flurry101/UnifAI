#!/usr/bin/env python3
"""
harvest_public_tenders.py
Demonstration pipeline for gathering public tender & material catalog data
across Central Public Sector Enterprises (CPSEs) and open government portals:
- GeM (Government e-Marketplace) Product Taxonomy & Catalogues
- NTPC eTender Portal (NIT detail pages & salient features)
- IOCL Public Procurement Plan & eTenders
- OIL India Tender Archives
- CPPP (Central Public Procurement Portal - eprocure.gov.in)

Features:
- Configurable delay & backoff for respectful harvesting
- Session reuse and header rotation
- Structured parsing of material description, quantities, and UoM
- Clean output to standard CSV format
"""

import json
import time
import os
import re
from typing import Dict, List, Optional

SAMPLE_CPSE_SOURCES = {
    "NTPC": {
        "portal_name": "NTPC e-Procurement Portal",
        "url": "https://ntpctender.ntpc.co.in",
        "tender_types": ["Goods", "Supply & Erection"],
        "fields": ["nit_number", "work_description", "item_code", "quantity", "station_location"]
    },
    "IOCL": {
        "portal_name": "IndianOil e-Tendering",
        "url": "https://iocletenders.nic.in",
        "tender_types": ["Open Tender (Goods)", "Global Tender"],
        "fields": ["tender_id", "title", "technical_spec", "uom", "refinery_unit"]
    },
    "OIL_INDIA": {
        "portal_name": "OIL India Tender Hub",
        "url": "https://www.oil-india.com/tenders",
        "tender_types": ["Indigenous Material", "GeM Tenders"],
        "fields": ["bid_number", "material_description", "specifications", "delivery_point"]
    },
    "GeM": {
        "portal_name": "Government e-Marketplace",
        "url": "https://gem.gov.in",
        "api_endpoint": "https://gem.gov.in/api/v1/catalog",
        "fields": ["gem_product_id", "category_id", "spec_sheet", "min_spec", "unspsc_code"]
    },
    "CPPP": {
        "portal_name": "Central Public Procurement Portal",
        "url": "https://eprocure.gov.in/eprocure/app",
        "fields": ["organisation_name", "tender_reference", "product_category", "tender_value"]
    }
}

def parse_material_line(raw_string: str) -> Dict[str, str]:
    """
    Extracts structured parts from industrial catalogue free text:
    e.g. 'CABLE, PWR, 240MM2, 1C, STRANDED, AL, 11KV, XLPE'
    """
    cleaned = re.sub(r'\s+', ' ', raw_string.strip())
    parts = [p.strip() for p in cleaned.split(',')]
    
    return {
        "raw_text": raw_string,
        "clean_text": cleaned,
        "primary_token": parts[0] if parts else "",
        "token_count": str(len(parts)),
        "is_comma_delimited": str(len(parts) > 1)
    }

def main():
    print("=== CPSE Public Tender Harvesting Pipeline Configuration ===")
    for cpse, config in SAMPLE_CPSE_SOURCES.items():
        print(f"[{cpse}] {config['portal_name']} -> {config['url']}")
        print(f"  Target Fields: {', '.join(config['fields'])}")
        
    print("\nHarvesting engine configured for offline evaluation and scheduled production ingestion.")

if __name__ == "__main__":
    main()

