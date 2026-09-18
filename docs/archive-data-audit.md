# Full Archive Audit Report

This document details the audit of all archived datasets in the repository, assessing their readiness for Dataset V2 and the UnifAI matching architecture.

## File: cpcl_procurement_proxy.csv
- **Location:** `archive/data\benchmark\cpcl_procurement_proxy.csv`
- **Format:** csv
- **Size:** 680 bytes
- **Row Count:** 3
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** org, code, description, plant, event_year, entity_key, erp_system, family
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: cpse_cross_sector_comprehensive_benchmark.csv
- **Location:** `archive/data\benchmark\cpse_cross_sector_comprehensive_benchmark.csv`
- **Format:** csv
- **Size:** 70109 bytes
- **Row Count:** 521
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** groundtruth_cluster_id, cpse_name, cpse_material_code, raw_material_description, unit_of_measure, match_label, item_category, target_unspsc_code, conflict_reason
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: cpse_cross_sector_groundtruth_benchmark.csv
- **Location:** `archive/data\benchmark\cpse_cross_sector_groundtruth_benchmark.csv`
- **Format:** csv
- **Size:** 4689 bytes
- **Row Count:** 29
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** groundtruth_cluster_id, cpse_name, cpse_material_code, raw_material_description, unit_of_measure, match_label, material_grade, dimensions_size, pressure_rating_spec, item_category, target_unspsc_code
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: cpse_real_world_provenance_benchmark.csv
- **Location:** `archive/data\benchmark\cpse_real_world_provenance_benchmark.csv`
- **Format:** csv
- **Size:** 106992 bytes
- **Row Count:** 481
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** cluster_id, canonical_material_name, target_unspsc, organization, source_portal, tender_reference, tender_id, raw_published_description, description_kind, quantity, unit, provenance_doc_url, is_genuine_public_data
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: cross_cpse_materials_sample.csv
- **Location:** `archive/data\benchmark\cross_cpse_materials_sample.csv`
- **Format:** csv
- **Size:** 414 bytes
- **Row Count:** 8
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** cpse, material_code, description, unit
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: labelled_duplicate_benchmark.csv
- **Location:** `archive/data\benchmark\labelled_duplicate_benchmark.csv`
- **Format:** csv
- **Size:** 612 bytes
- **Row Count:** 5
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** row_key, query, expected_code, label, plant, event_year, entity_key, split
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: national_master_schema_sample.csv
- **Location:** `archive/data\benchmark\national_master_schema_sample.csv`
- **Format:** csv
- **Size:** 483 bytes
- **Row Count:** 2
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** national_material_code, standardized_description, category, material, diameter_mm, length_mm, size_mm, pressure_rating_psi, connection_type, bearing_number, seal_type, wall_thickness_mm, pipe_type, cpse_mappings, source_group, member_count, status
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: piping_catalog_sample.jsonl
- **Location:** `archive/data\benchmark\piping_catalog_sample.jsonl`
- **Format:** jsonl
- **Size:** 631 bytes
- **Row Count:** N/A (not CSV)
- **Classification:** `LABELLED_BENCHMARK`
- **Columns:** 
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: bhel_tenders.csv
- **Location:** `archive/data\corpus\bhel_tenders.csv`
- **Format:** csv
- **Size:** 8311 bytes
- **Row Count:** 20
- **Classification:** `REAL_PUBLIC_SOURCE`
- **Columns:** tender_id, organization, manufacturing_unit, location, category, description, uom, quantity, source_portal, source_url
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** Yes
- **Supports Attribute Extraction:** Yes
- **Supports Retrieval:** Yes

## File: coal_india_tenders.csv
- **Location:** `archive/data\corpus\coal_india_tenders.csv`
- **Format:** csv
- **Size:** 9152 bytes
- **Row Count:** 25
- **Classification:** `REAL_PUBLIC_SOURCE`
- **Columns:** tender_id, organization, subsidiary_or_unit, location, category, description, uom, quantity, source_portal, source_url
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** Yes
- **Supports Attribute Extraction:** Yes
- **Supports Retrieval:** Yes

## File: cppp_tender_items.csv
- **Location:** `archive/data\corpus\cppp_tender_items.csv`
- **Format:** csv
- **Size:** 4750 bytes
- **Row Count:** 23
- **Classification:** `REAL_PUBLIC_SOURCE`
- **Columns:** org, tender_ref, category, description, location, uom, quantity
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** Yes
- **Supports Attribute Extraction:** Yes
- **Supports Retrieval:** Yes

## File: cpse_material_corpus.csv
- **Location:** `archive/data\corpus\cpse_material_corpus.csv`
- **Format:** csv
- **Size:** 6278770 bytes
- **Row Count:** 21513
- **Classification:** `REAL_PUBLIC_SOURCE`
- **Columns:** corpus_id, organization, source_system, source_section, tender_reference, tender_id, description, description_kind, item_type_hint, quantity, unit, location, product_category, document_url, source_url
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** Yes
- **Supports Attribute Extraction:** Yes
- **Supports Retrieval:** Yes

## File: gem_catalog_items.csv
- **Location:** `archive/data\corpus\gem_catalog_items.csv`
- **Format:** csv
- **Size:** 7178 bytes
- **Row Count:** 44
- **Classification:** `REAL_PUBLIC_SOURCE`
- **Columns:** gem_item_code, source_portal, category_id, category_name, unspsc_code, item_description, standard_uom, target_sector
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** Yes
- **Supports Attribute Extraction:** Yes
- **Supports Retrieval:** Yes

## File: sail_tenders.csv
- **Location:** `archive/data\corpus\sail_tenders.csv`
- **Format:** csv
- **Size:** 6976 bytes
- **Row Count:** 20
- **Classification:** `REAL_PUBLIC_SOURCE`
- **Columns:** tender_id, organization, plant_unit, location, category, description, uom, quantity, source_portal, source_url
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Yes
- **Supports Normalization:** Yes
- **Supports Attribute Extraction:** Yes
- **Supports Retrieval:** Yes

## File: maximo_asset_export.csv
- **Location:** `archive/data\erp_mocks\maximo_asset_export.csv`
- **Format:** csv
- **Size:** 8759 bytes
- **Row Count:** 60
- **Classification:** `ERP_MOCK`
- **Columns:** ITEMNUM, DESCRIPTION, ITEMSETID, ITEMTYPE, ORDERUNIT, ISSUEUNIT, COMMODITYGROUP, COMMODITY, STATUS, ROTATING, SITEID, LOCATION, CURBAL, UNITCOST, NATIONAL_ID
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Varies
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: oracle_fusion_export.csv
- **Location:** `archive/data\erp_mocks\oracle_fusion_export.csv`
- **Format:** csv
- **Size:** 8853 bytes
- **Row Count:** 60
- **Classification:** `ERP_MOCK`
- **Columns:** ITEM_NUMBER, ITEM_DESCRIPTION, ORGANIZATION_CODE, PRIMARY_UOM_CODE, SECONDARY_UOM_CODE, ITEM_CLASS_NAME, ITEM_TYPE, ITEM_STATUS, UNIT_COST, GLOBAL_ATTRIBUTE1
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Varies
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: sap_ecc_mara_export.csv
- **Location:** `archive/data\erp_mocks\sap_ecc_mara_export.csv`
- **Format:** csv
- **Size:** 7117 bytes
- **Row Count:** 60
- **Classification:** `ERP_MOCK`
- **Columns:** MATNR, MAKTX, MEINS, BSTME, MATKL, MTART, WERKS, LGORT, BKLAS, VPRSV, VERPR, STPRS, EXTWG
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Varies
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: sap_matmas05_sample.xml
- **Location:** `archive/data\erp_mocks\sap_matmas05_sample.xml`
- **Format:** xml
- **Size:** 2544 bytes
- **Row Count:** N/A (not CSV)
- **Classification:** `ERP_MOCK`
- **Columns:** 
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Varies
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: sap_s4hana_odata_response.json
- **Location:** `archive/data\erp_mocks\sap_s4hana_odata_response.json`
- **Format:** json
- **Size:** 5056 bytes
- **Row Count:** N/A (not CSV)
- **Classification:** `ERP_MOCK`
- **Columns:** 
- **Contains Descriptions:** Yes
- **Contains Tech Attributes:** Varies
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: cppp_product_categories.csv
- **Location:** `archive/data\reference\cppp_product_categories.csv`
- **Format:** csv
- **Size:** 3950 bytes
- **Row Count:** 94
- **Classification:** `REFERENCE_DATA`
- **Columns:** select_name, value, label
- **Contains Descriptions:** Varies
- **Contains Tech Attributes:** Varies
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No

## File: ireps_unified_pl_directory.csv
- **Location:** `archive/data\reference\ireps_unified_pl_directory.csv`
- **Format:** csv
- **Size:** 7042 bytes
- **Row Count:** 47
- **Classification:** `REFERENCE_DATA`
- **Columns:** pl_no, main_group, group_name, description, uom, standard_spec
- **Contains Descriptions:** Varies
- **Contains Tech Attributes:** Varies
- **Supports Normalization:** No
- **Supports Attribute Extraction:** No
- **Supports Retrieval:** No
