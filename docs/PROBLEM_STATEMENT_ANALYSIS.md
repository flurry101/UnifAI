# Problem Statement Deep-Dive:

## AI-Driven Standardization & Harmonization of Material Codes Across CPSEs

**Problem ID:** SIH26099  
**Sponsoring Ministry:** Ministry of Petroleum & Natural Gas (MoPNG)  
**Sponsoring CPSE / Department:** Chennai Petroleum Corporation Limited (CPCL) / Indian Oil Corporation Limited (IOCL)  
**Target Sectors:** Oil & Gas, Power, Steel, Mining, Heavy Engineering  
**Vision:** One Nation, One Material Code' 
> Common National Material Code (CNMC)

---

## 1. Word-by-Word Deconstruction of the Problem Statement

### A. Background
> *"Central Public Sector Enterprises (CPSEs) operating in sectors such as Oil & Gas, Power, Steel, Mining and Heavy Engineering procure and maintain a large number of similar or functionally equivalent materials."*

- **"Central Public Sector Enterprises (CPSEs)":** State-owned enterprises under the Government of India (Maharatnas, Navratnas, Miniratnas) such as ONGC, IOCL, GAIL, HPCL, BPCL (Oil & Gas); NTPC, NHPC, POWERGRID (Power); SAIL, RINL (Steel); Coal India Limited, NMDC (Mining); BHEL, BEL (Heavy Engineering).
- **"Operating in sectors...":** Each sector has specialized operating environments, harsh temperatures, explosive atmospheres, and high mechanical stresses. Yet they share massive cross-sector procurement of general engineering items (fasteners, structural steel, industrial valves, pipes, flanges, electrical cables, switchgear, bearings, instrumentation, and consumables).
- **"Similar or functionally equivalent materials":** Items that serve the exact same engineering function (e.g., an SKF 6205-2RS deep groove ball bearing, an ASTM A105 6-inch 150# Weld Neck Flange, or a 3-core 240 sq.mm 11kV XLPE power cable) even if catalogued under different names, abbreviations, or internal part numbers.

> *"However, the same material may be assigned different material codes, descriptions, specifications, units of measurement and classification across different CPSEs."*

- **"Different material codes":** Legacy proprietary numbering schemes (e.g., ONGC's 8-digit material code vs. SAIL's 10-digit SAP code vs. IOCL's 9-digit alphanumeric key vs. BHEL's drawing/pattern-based numbering).
- **"Inconsistent descriptions":** Free-text variations, spelling permutations, and abbreviation styles:
  - *Example:* `"HEX BOLT M10 X 50 SS304"` (ONGC) vs `"SS 304 HEXAGONAL BOLT 10MM X 50MM"` (BHEL) vs `"HEX BOLT M10*50 STAINLESS STEEL 304"` (SAIL) vs `"HEXAGONAL BOLT M10 X 50 MM SS304 DIN 933"` (NTPC).
- **"Specifications & technical parameters":** Attributes buried inside unstructured text strings (metallurgy grades like ASTM A216 WCB, ASME B16.5 pressure classes like 150# or 300#, dimensions, temperature limits).
- **"Units of measurement (UoM)":** Mismatched units representing the same physical quantity:
  - Count: `EA` (Each), `NOS` (Numbers), `PCS` (Pieces), `SET`, `ST`.
  - Length: `MTR` (Meters), `M`, `FEET`, `INCH`, `MM`.
  - Mass: `KG`, `MT` (Metric Tonnes), `QUINTAL`.
  - Pressure: `LBS`, `PSI`, `BAR`, `KG/CM2`, `PN`.
- **"Classification":** Different taxonomic trees (MESC - Material and Equipment Standards Code in Oil & Gas, internal SAP Material Groups, custom CPSE commodity buckets, or CPPP product categories).

> *"This results in duplication of material masters, inconsistent descriptions, difficulty in identifying equivalent materials, fragmented procurement data, higher inventory levels and limited opportunities for collaborative procurement."*

- **"Duplication of material masters":** Bloated ERP databases where the same plant or multiple CPSEs hold redundant master records.
- **"Fragmented procurement data":** Each CPSE tenders separately on disparate portals (CPPP, GeM, IREPS, internal SAP SRM), making national spend analysis impossible.
- **"Higher inventory levels":** Billions of rupees in working capital locked in buffer safety stock across neighboring CPSE plants (e.g., an ONGC offshore terminal and an IOCL refinery 15 km apart holding duplicate high-value emergency spare valves because neither knows the other has it in stock).
- **"Limited collaborative procurement":** Inability to aggregate buying volume across CPSEs to negotiate bulk discounts on common commodities.

---

### B. Core Capabilities Required by the Solution

1. **AI-Based Matching of Material Descriptions and Specifications:**
   - Multi-modal matching: combining semantic representation (sentence embeddings), string-distance token metrics (RapidFuzz), and domain-specific engineering rule parsers.
2. **Identification of Duplicate, Near-Duplicate, and Equivalent Materials:**
   - **Identical / Exact Duplicate:** Exact physical and specification match (100% interchangeable).
   - **Near-Duplicate:** Same physical item with trivial cosmetic variations (casing, word order, non-critical whitespace).
   - **Functionally Equivalent:** Meets equivalent engineering standards (e.g., DIN 933 vs ISO 4017 bolt, or equivalent API 600 gate valves from different certified manufacturers).
   - **Incompatible Conflict (Crucial):** Similar text but incompatible engineering properties (e.g., Class 150 vs Class 300; Carbon Steel vs Stainless Steel; 11kV vs 33kV insulation). Merging these is dangerous; the engine must actively block them.
3. **Automated Standardization of Descriptions & Attributes:**
   - Canonical format generation: `[ITEM_TYPE] [PRIMARY_DIMENSIONS] [MATERIAL_GRADE] [PRESSURE/VOLTAGE_RATING] [STANDARD_CODE]`.
4. **Intelligent Classification & Categorization:**
   - Auto-mapping items into universal industrial taxonomies: **UNSPSC** (United Nations Standard Products and Services Code), **GeM / CPPP** standard product directories, **ISO 14224** (9-level international reliability and maintenance taxonomy tailored for MoPNG, CPCL, ONGC, and IOCL refinery asset equipment), and **eClass** (for heavy machinery and digital twins).
5. **Generation of a Common National Material Code (CNMC):**
   - A deterministic, structured, transparent identifier:
     `CNMC-[UNSPSC_COMMODITY]-[CATEGORY_ABBR]-[KEY_ATTR_HASH]`
     (e.g., `CNMC-31161601-BLT-SS304-M10-L050`).
6. **CPSE Code Mapping & Traceability:**
   - Strict retention of original CPSE legacy codes in an append-only mapping table. No legacy code is ever overwritten or broken.
7. **User Validation and Approval Workflow (Human-in-the-Loop):**
   - High confidence (\(\ge 85\%\)): Auto-link recommendation with instant audit log.
   - Ambiguous / Medium confidence (\(60\% - 84\%\)): Flagged to Human Review Queue with side-by-side spec comparison and explainability score.
   - Low confidence / Conflict (\(< 60\%\)): Kept segregated as distinct items with conflict reason logged.
8. **Dashboard for Material Master Analytics & Spend Optimization:**
   - Duplicate detection metrics, spend aggregation potential, inventory visibility across plants.
9. **Audit Trail & Governance:**
   - Immutable audit logs (who approved, timestamp, rationale, previous vs. updated code).
10. **SAP / ERP Integration Capability:**
    - Support for SAP RFC/BAPI (`BAPI_MATERIAL_SAVEDATA`), IDoc `MATMAS05` formats, S/4HANA OData REST endpoints, and bulk CSV/Excel upload/export.

---

## 2. Multi-Stakeholder Matrix

| Stakeholder Persona | Core Needs & Frustrations | System Capabilities Delivered |
|---|---|---|
| **CPSE Procurement Officers & Buyers** (ONGC, IOCL, NTPC, SAIL, BHEL) | Tendering same items with fragmented specs; lengthy cycle times to write NIT technical parameters; zero visibility into prices paid by sister CPSEs. | Instant search for pre-standardized material specifications; visibility into inter-CPSE bulk demand aggregation; faster tender document generation. |
| **CPSE Master Data Managers & Cataloguers** | Inundated with tens of thousands of duplicate item requests in SAP/Maximo; manual cleanup is tedious and error-prone. | Rule-based auto-extraction of attributes, AI candidate matching, one-click review/approval workbench, seamless export back to ERP. |
| **Plant Storekeepers & Warehouse Engineers** | Working in noisy plant/refinery environments; need quick identification of spare parts. | Low-latency catalog search workbench; mobile/tablet-friendly PWA interface; barcode/QR code mapping. [Optional Extension: Voice-assisted input for hands-free shop-floor lookups]. |
| **Central Vigilance Commission (CVC) & CAG Auditors** | Mandate full transparency in public procurement; suspicion of biased proprietary part descriptions; strict scrutiny of master data modifications. | Cryptographic tamper-evident audit logs; complete explanation of AI match scores; transparent lineage tracing back to original source tender/PO. |
| **Ministry of Petroleum & Natural Gas (MoPNG) / DPE Leadership** | Lack of macro-level spend visibility across CPSEs; duplicate buffer inventory locking public funds. | Executive national dashboard; cross-CPSE demand pooling analytics; projected procurement savings calculator. |
| **Vendors / MSME Suppliers on GeM** | Confused by varying CPSE tender specs for identical industrial goods; high barrier to entry. | Harmonized UNSPSC / GeM specifications enabling standardized bidding across multiple CPSE contracts. |

---

## 3. Critical Non-Functional Architectural Principles

### A. Core Master Data Governance & Usability
- **Zero-Clutter Approval Workbench:** Clear side-by-side diff of proposed vs. legacy descriptions, with highlighted conflicting or matching attributes.
- **Transparent Explainability:** Match score broken down into `Text Similarity (50%)`, `Spec Compatibility (35%)`, and `Unit Normalization (15%)` rather than a black-box AI percentage.
- **Accessible UI Standards:** Full WCAG 2.1 AA compliance, high contrast color palettes, screen-reader accessible tables, and complete keyboard navigability for enterprise government desktops.

### B. Scalability & Production Build Stack
- **Sub-Second Retrieval over 1,000,000+ Items:** PostgreSQL `pgvector` HNSW vector indexing utilizing `halfvec` 16-bit scalar quantization to halve RAM footprint.
- **Iterative Index Scanning:** `hnsw.iterative_scan = 'relaxed_order'` to resolve SQL metadata pre-filtering without degrading vector recall.
- **Dual-Engine Hybrid Retrieval:** Reciprocal Rank Fusion (RRF) combining sparse lexical BM25 (`tsvector`) for part numbers with dense HNSW semantic search.
- **Deterministic Tooling:** Managed via `python-uv` for deterministic, sub-second dependency installation across government air-gapped CI/CD environments.

### C. Feasibility & Air-Gapped Offline Operation
- **Enterprise Intranet Requirement:** Many CPSEs (especially in defense, energy, and nuclear sectors) operate on secure air-gapped intranets with strict data-residency laws preventing master data from leaving the network.
- **Zero Cloud Hard Dependency:** The core matching engine runs 100% locally with offline sentence-transformers (`all-MiniLM-L6-v2` / `BAAI/bge-small-en-v1.5`), deterministic rule extractors, and local PostgreSQL / SQLite storage. External LLM APIs (Gemini/OpenAI) are strictly optional advisory layers.

---

## 4. [Optional / Non-Core Extension] Multilingual Speech & Edge Offline Voice Support

### Why Multilingual & Voice Support Are Optional Extensions:
1. **ERP Material Master Language Reality:**  
   Across all Central Public Sector Enterprises, ERP material master tables (`MARA/MAKT` in SAP, `EGP_SYSTEM_ITEMS_B` in Oracle, `ITEM` in Maximo) are strictly cataloged in **standard technical English** using international alphanumeric engineering codes (e.g., `VLV BL 2IN CL150 RF CS FLGD A216 WCB`). Enterprise ERP databases do not maintain material codes in regional languages.
2. **Core Mandate Alignment (SIH26099):**  
   The fundamental problem statement is defined as *"AI-Driven Standardization and Harmonization of Material Codes Across CPSEs"*. The primary challenges are **backend algorithmic problems**: resolving text heterogeneity, acronym expansion (`VLV`, `BL`, `NRV`), metric/imperial unit conversion, hierarchical taxonomy classification (UNSPSC, ISO 14224), and enforcing non-negotiable engineering safety gates (SS304 vs SS316, Class 150 vs Class 300).
3. **Architectural Decoupling & Reliability:**  
   Vernacular speech translation (Digital India Bhashini, Sarvam AI) and edge voice assistants (VEXYL AI on-prem telephony gateway, offline Whisper) are **peripheral front-end convenience layers** designed solely for plant-floor storekeepers wearing safety gear. They do not alter or participate in the core deduplication and harmonization algorithms.  
   Treating them as strictly optional, disableable modules ensures that the core master data system remains lightweight, deterministic, auditable, and unburdened by heavyweight acoustic model dependencies during deployment.



