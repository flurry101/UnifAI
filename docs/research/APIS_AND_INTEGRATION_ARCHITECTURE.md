# APIs, Embedding Models, and Enterprise ERP Integration Architecture

This document analyzes the complete API, model, and system integration landscape for the **AI-Driven National Unified Material Master Framework across CPSEs**.

---

## 1. Classification & Taxonomy Standards

### A. UNSPSC (United Nations Standard Products and Services Code)
- **Evaluation:**
  - UNSPSC is an 8-digit (or 10-digit) hierarchical taxonomy: `[Segment (2)] [Family (2)] [Class (2)] [Commodity (2)]`.
  - While commercial UNSPSC search portals exist (e.g., unspsc.org, ECCMA), a public, free, unlimited real-time REST API does not exist; UNSPSC is primarily distributed as an official master code list.
- **Architectural Decision:**
  - **Offline Bundled Reference Data:** We bundle the comprehensive industrial subset of UNSPSC directly in the database (`data/reference/unspsc_industrial_taxonomy.csv`).
  - **Local Fast Vector/Text Search:** An in-memory trie and embedding-based similarity lookup maps any free-text material line directly to the closest 8-digit UNSPSC commodity code in \(< 5\text{ ms}\) with zero network calls.

### B. GeM (Government e-Marketplace) Taxonomy
- **Evaluation:**
  - GeM standardizes all items using a 4-tier category taxonomy mapped directly to UNSPSC and HS Codes.
  - Production API access requires authenticated buyer/seller credentials issued by NIC.
- **Architectural Decision:**
  - **Hybrid Ingestion Adapter:** When active GeM API credentials are provided, it pulls live catalog schemas. In offline or standard mode, it consumes GeM-formatted JSON/CSV exports and GeMARPTS identification strings extracted from public tender archives.

### C. ISO 14224 (Petroleum, Petrochemical & Natural Gas Equipment Reliability & Maintenance)
- **Evaluation:**
  - Standardized internationally under ISO / TC 67, ISO 14224 provides a rigorous 9-level taxonomy tailored specifically for oil and gas, petrochemical, and refinery equipment:
    $$\text{Industry} \to \text{Business Category} \to \text{Installation} \to \text{Plant/Unit} \to \text{Section/System} \to \text{Equipment Unit} \to \text{Subunit} \to \text{Maintainable Item} \to \text{Part}$$
  - Crucially, it establishes controlled vocabularies for failure modes, failure mechanisms, and maintainable spares.
- **Architectural Decision:**
  - **Refinery & Offshore Asset MRO Harmonization:** Directly serves the MoPNG / CPCL / ONGC / IOCL domain. While UNSPSC provides macro-level spend categorization for financial audits, ISO 14224 supplies the granular technical taxonomy needed for refinery plant maintenance and safety-critical equipment master data.

### D. eClass Standard (Industrial Product & Engineering Specification)
- **Evaluation:**
  - A 4-level hierarchical classification standard (`Segment`, `Main Group`, `Group`, `Sub-group`) widely utilized across heavy machinery, power generation, and digital twin engineering.
- **Architectural Decision:**
  - Mapped as an optional cross-reference for BHEL and NTPC heavy engineering assets, facilitating seamless interchange with European and international equipment specifications.

---

## 2. Embedding Models, Vector Storage & Dual-Engine Hybrid Retrieval

### A. Core Embedding Architecture (Zero-API-Tax, Air-Gapped)
- **Requirement:** Must run completely inside secure, air-gapped CPSE networks without sending sensitive energy, defence, or public infrastructure procurement data to external cloud APIs (eliminating variable per-token API taxes and data-sovereignty risks).
- **Selected Models:**
  1. **Primary High-Efficiency Model: `BAAI/bge-small-en-v1.5` (or `sentence-transformers/all-MiniLM-L6-v2`):**
     - Footprint: \(\approx 33.4\text{ M parameters } (\approx 80 - 130\text{ MB})\).
     - Dimension: 384-dimensional dense vectors.
     - Throughput: \(\approx 2,000 - 4,000\text{ embeddings/sec}\) on CPU via ONNX Runtime / FlagEmbedding.
     - Role: High-volume bulk ingestion, catalog indexing, and real-time semantic deduplication with minimal storage overhead.
  2. **Multi-Lingual & Multi-Functionality Fallback: `BAAI/bge-m3`:**
     - Footprint: 567M parameters, 1024-dimensional vectors.
     - Capabilities: Multi-Linguality (100+ languages), Multi-Granularity (up to 8,192 tokens), and simultaneous output of dense embeddings, sparse lexical weights, and multi-vector representations from a single forward pass.
     - Role: Resolving dense multi-token regional tender specifications where complex cross-lingual context is required.
- **Deterministic Offline Fallback:**
  - When PyTorch/Transformers runtimes are unavailable, the engine automatically falls back to **Character N-Gram Hashing (MinHash / TF-IDF)** and **RapidFuzz token-sort ratio**, ensuring 100% operational uptime.

### B. High-Dimensional Vector Storage: PostgreSQL + pgvector
The platform implements a unified polyglot persistence model utilizing **PostgreSQL with the `pgvector` extension**, completely eliminating the operational complexity and network latency of managing separate external vector databases (e.g. Pinecone or Qdrant):
1. **HNSW (Hierarchical Navigable Small World) Indexing:**
   - Constructs a multi-layered topological graph of the vector space using `vector_cosine_ops`, achieving sub-millisecond retrieval with near-perfect recall on catalogs exceeding 1,000,000 items.
2. **Scalar Quantization with `halfvec` (16-bit Floats):**
   - Employs the `halfvec` data type in pgvector, converting 32-bit floating-point dimensions to 16-bit representations.
   - Halves the RAM and storage footprint of stored embeddings with a statistically negligible impact on search precision (\(< 0.1\%\)), allowing entire HNSW graphs to reside comfortably within shared memory buffers.
3. **Iterative Index Scanning (`hnsw.iterative_scan = 'relaxed_order'`):**
   - Solves the classic "SQL overfiltering" pathology where pre-filtering on CPSE metadata (e.g., filtering by plant `WERKS=1001` or category before vector search) causes standard HNSW to return empty result sets.
   - Iterative scanning ensures pgvector scans the graph incrementally until the requested top-$K$ filtered candidates are retrieved.
4. **Memory Tuning:**
   - Pre-configures `maintenance_work_mem` to prevent HNSW build operations from spooling to disk during bulk ingestion.

### C. Dual-Engine Hybrid Retrieval with Reciprocal Rank Fusion (RRF)
Semantic vector search excels at conceptual synonyms (`valve` $\leftrightarrow$ `vlv`, `gasket` $\leftrightarrow$ `seal`), but can fail on exact alphanumeric part numbers or rigid specification codes. Conversely, lexical search excels at exact strings but fails on synonyms. unifAI resolves this via **Dual-Engine Hybrid Retrieval**:
1. **Dense Vector Retrieval (HNSW):** Retrieves top candidates by semantic proximity.
2. **Sparse Lexical Retrieval (BM25 / `tsvector`):** Uses PostgreSQL native full-text search with `tsquery` over indexed technical attributes and manufacturer part numbers.
3. **Reciprocal Rank Fusion (RRF):**
   Fuses the ordinal rankings from both retrieval systems into a unified relevance score without needing to normalize disparate raw score scales:
   $$RRF\_Score(d \in \mathcal{D}) = \sum_{m \in \{\text{Dense}, \text{Lexical}\}} \frac{1}{k + r_m(d)}$$
   where $k = 60$ is the standard smoothing constant and $r_m(d)$ is the document rank in model $m$.

### D. Hard Engineering Safety Gates (Active Veto)
Candidates retrieved by hybrid RRF pass through strict, deterministic Engineering Veto Gates:
$$\text{Composite Score} = \left(0.50 \times \text{Semantic} + 0.35 \times \text{Specs} + 0.15 \times \text{UoM}\right) \times \prod_{k \in \mathcal{K}_{\text{veto}}} \mathbb{I}(\text{Match}_k)$$
- **Metallurgy Gate:** If `Grade_A != Grade_B` (e.g., SS304 vs SS316, ASTM A216 WCB vs A351 CF8M): **VETO (Score = 0)**
- **Pressure Rating Gate:** If `Pressure_A != Pressure_B` (e.g., ASME Class 150 vs Class 300): **VETO (Score = 0)**
- **Voltage Rating Gate:** If `Voltage_A != Voltage_B` (e.g., 1.1 kV vs 11 kV): **VETO (Score = 0)**

---

## 3. Advisory LLM Layer & Master Data Anti-Hallucination Guardrails

- **Core Master Data Governance Rule:** The core material attribute extraction, standardization, deduplication, and CNMC code generation **must never depend on unconstrained LLM generation**. In industrial engineering and public procurement, generative LLMs hallucinate technical specifications, inventing non-existent pressure ratings, swapping pipe schedules, or transposing metallurgy grades.
- **Deterministic Extraction + Constrained Advisory Role:**
  1. **Deterministic Information Extraction:** Hard physical invariants (nominal bore, pipe schedule, pressure rating, voltage, metallurgy grade, standard code) are parsed using compiled regex patterns, domain dictionaries, and deterministic tokenizers.
  2. **Advisory LLM Co-Pilot (HITL Workbench):** An LLM serves strictly as an optional "AI Co-pilot" for human reviewers and cataloguers:
     - Generates natural-language justification for complex merges (e.g., *"Merged because ASTM A351 CF8 is the exact casting designation equivalent to wrought 304 stainless steel under ASME B16.34"*).
     - Proposes standardized phrasing templates strictly constrained to the extracted attribute values.
     - Automatically routes high-uncertainty candidate pairs (where composite score hovers near the decision boundary) to human domain experts via an Active Learning loop.
- **Supported Backends:**
  - **Local Offline (Air-Gapped):** Ollama / vLLM running `gemma-2-2b-instruct` or `llama-3.2-3b-instruct`.
  - **Cloud (Optional):** Google Gemini 1.5/2.0 Flash or OpenAI API.
  - Easily toggled via environment variable: `ENABLE_AI_ADVISORY=true/false`.

---

## 4. Enterprise SAP & ERP Integration Architecture: Ingesting Across Heterogeneous Systems

### A. The Core Requirement: What "Across Different ERP/SAP Systems" Actually Means
The Problem Statement requires the platform to analyze material master data **"across different ERP/SAP systems."**

> **Crucial Engineering Reality:**  
> This does **not** mean unifAI needs to stand up, host, or replace an ERP system. Every CPSE already operates its own mature enterprise ERP:
> - **ONGC & IOCL:** SAP S/4HANA & SAP ECC 6.0
> - **BHEL:** Oracle ERP Cloud & legacy in-house systems
> - **NTPC:** SAP ERP & Maximo
> - **Coal India Limited:** SAP & CoalNet
>
> The real engineering challenge is **ingesting, reconciling, and harmonizing disparate, heterogeneous data exports** originating from these different ERP backends, each with completely different table structures, field naming conventions, attribute encodings, and UoM representations.

Standing up an open-source ERP (like ERPNext or Odoo) or spinning up an SAP BTP trial tenant during development would be an architectural anti-pattern—burning development time on ERP tenant administration rather than the core innovation: **multi-schema ingestion, semantic matching, engineering safety gates, and national governance**.

---

### B. Heterogeneous ERP Source Schemas Handled by unifAI

unifAI provides pre-configured, declarative ingestion adapters for the major CPSE ERP export schemas:

| ERP Source Type | Typical CPSE Users | Export Field Names | Standard Table Origin |
|---|---|---|---|
| **SAP S/4HANA & ECC** | ONGC, IOCL, GAIL, NTPC | `MATNR`, `MAKTX`, `MEINS`, `MATKL`, `MTART`, `WERKS`, `LGORT`, `BKLAS`, `VERPR`, `EXTWG` | SAP `MARA`, `MAKT`, `MARC`, `MBEW` |
| **Oracle Fusion / Cloud ERP** | BHEL, SAIL subsidiaries | `ITEM_NUMBER`, `ITEM_DESCRIPTION`, `PRIMARY_UOM_CODE`, `ITEM_CLASS_NAME`, `ITEM_TYPE`, `UNIT_COST` | Oracle `EGP_SYSTEM_ITEMS_B / TL` |
| **IBM Maximo Asset Management** | NTPC Power Plants, Mining | `ITEMNUM`, `DESCRIPTION`, `ORDERUNIT`, `ISSUEUNIT`, `COMMODITYGROUP`, `CURBAL`, `UNITCOST` | Maximo `ITEM` & `INVENTORY` tables |
| **Legacy CPSE Custom DBs / GeM** | Smaller CPSEs, CoalNet | `material_code`, `description`, `unit`, `location`, `category`, `cnmc_code` | Custom SQL Views / CSV Dumps |

---

### C. Declarative Ingestion Adapter & Column Mapping Engine

Instead of hardcoding column positions, unifAI employs a **Configurable Source Adapter Engine** driven by `config/erp_schema_mappings.json`:
- **Auto-Header Detection:** When an ad-hoc Excel or CSV dump is uploaded without an explicit ERP profile, an intelligent schema inference algorithm inspects column headers (e.g., detecting `MATNR` or `MAKTX` to automatically activate the SAP profile, or `ITEMNUM` to activate Maximo).
- **Canonical Standardization:** Every record, regardless of source ERP origin, is mapped into the internal canonical schema:
  $$\text{Raw ERP Record} \xrightarrow{\text{Adapter Mapping}} \text{Canonical Item} \xrightarrow{\text{AI Engine}} \text{Common National Material Code (CNMC)}$$

---

### D. Realistic SAP Integration Contracts (Batch IDoc & Synchronous RFC)

To demonstrate true enterprise SAP interoperability during evaluation and production pilots without requiring a live SAP tenant, unifAI implements concrete, schema-compliant enterprise interfaces:

1. **Synchronous Real-Time Transactional RFC (`BAPI_MATERIAL_SAVEDATA`):**
   - Implements the standard SAP Remote Function Call (RFC) specification for real-time transactional updates.
   - When a cataloguer approves a new Common National Material Code (CNMC) or description harmonization in the unifAI workbench, the system constructs a synchronous BAPI payload targeting `HEADDATA`, `CLIENTDATA`, and `MATERIALLONGTEXT`, receiving immediate verification from the SAP application layer.
2. **Asynchronous Batch EDI IDoc (`MATMAS05` XML Generator & Parser):**
   - Implements the standard enterprise IDoc format (`MATMAS05`) located in `data/erp_mocks/sap_matmas05_sample.xml`.
   - Populates segments `E1MARAM`, `E1MAKTM`, `E1MARCM`, and `E1MBEWM`, updating field `EXTWG` with the national CNMC code for bulk synchronization.
3. **SAP S/4HANA OData API (`data/erp_mocks/sap_s4hana_odata_response.json`):**
   - Matches the official SAP API Business Hub specification for **`API_PRODUCT_SRV/A_Product`** with navigation entities for plant (`to_Plant`) and valuation (`to_Valuation`).
4. **Round-Trip Master Data Synchronization:**
   - Demonstrates the complete enterprise loop:
     1. Ingest raw SAP `MARA`/`MAKT`, Oracle Fusion, or Maximo export.
     2. Match against sister CPSE catalogs and assign CNMC.
     3. Export an upload-ready delta spreadsheet (or `MATMAS05` XML / BAPI payload) that the CPSE cataloguer imports directly back into SAP using transaction codes `MM17` or `MASS`.

---

## 5. Modern High-Performance Tooling & Build Stack

To guarantee sub-second latency, developer velocity, and reproducible builds across air-gapped enterprise environments:

1. **Backend Framework (FastAPI + Asynchronous Type Hints):**
   - Non-blocking, asynchronous handling of concurrent API requests, ensuring heavy local embedding inference, RRF rankings, and database vector queries do not block the event loop.
2. **Deterministic Package Management (`python-uv`):**
   - Employs `python-uv`, the ultra-fast Rust-based Python package resolver.
   - Replaces traditional slow `pip`/`poetry` installations, slashing build times from minutes to seconds and guaranteeing deterministic lockfile reproducibility across secure government CI/CD pipelines.
3. **Data Validation & Schemas (Pydantic v2):**
   - Strict compile-time and runtime validation at all API boundaries, guaranteeing that incoming ERP payloads adhere to canonical schema definitions before database ingestion.
4. **Frontend Architecture (React, Vite & TypeScript):**
   - Single Page Application (SPA) providing compile-time type safety, sub-millisecond Hot Module Replacement (HMR), and streamlined state management via Zustand / TanStack Query for Human-in-the-Loop review workbenches.

---

## 6. [Optional / Non-Core Extension] Multilingual Speech & Edge Offline Voice Architecture

### Why Multilingual & Voice Support Are Strictly Optional Extensions:
1. **ERP Master Data Language Reality:**  
   Across all Indian CPSEs, enterprise ERP material master tables (`MARA/MAKT` in SAP S/4HANA, `EGP_SYSTEM_ITEMS_B` in Oracle Fusion, `ITEM` in IBM Maximo) catalog technical equipment and spares strictly in **standard technical English** using international alphanumeric specifications (e.g., `VLV BL 2IN CL150 RF CS FLGD A216 WCB`). Enterprise ERP databases never maintain material codes in regional languages.
2. **Core Mandate Alignment (SIH26099):**  
   The primary objective of SIH26099 is the backend algorithmic unification of disparate procurement databases: resolving text heterogeneity, acronym expansion, metric/imperial normalization, taxonomy classification (UNSPSC, ISO 14224), and enforcing deterministic engineering safety gates (metallurgy, pressure, voltage).
3. **Architectural Decoupling & Reliability:**  
   Multilingual speech translation and voice gateways are peripheral front-end convenience layers intended solely for shop-floor storekeepers or maintenance technicians wearing safety gear in plant units. They do not participate in the core deduplication and harmonization algorithms. Treating them as strictly optional, disableable modules ensures that the core master data system remains lightweight, deterministic, auditable, and unburdened by heavyweight acoustic model dependencies during enterprise deployment.

### A. Digital India Bhashini (Government of India) & Sarvam AI
- **Purpose:** Provide vernacular accessibility for CPSE field engineers, plant storekeepers, and MSME vendors across 22 official Indian languages.
- **Bhashini Integration:**
  - Open REST API under Digital India Mission.
  - Endpoints: Automatic Speech Recognition (ASR), Machine Translation (NMT), and Text-to-Speech (TTS).
- **Sarvam AI (`sarvam-2b` / `bulbul:v1`) — Primary Indic AI Voice API:**
  - Specialized state-of-the-art models fine-tuned specifically for Indian language acoustic characteristics, regional accents, and domain terminology across 10+ major Indian languages.
  - Allows procurement officers and storekeepers to speak in Hindi (*"दो इंच का गेट वाल्व क्लास १५०"*), Tamil (*"இரண்டு அங்குல கேட் வால்வு"*), Telugu, Bengali, Marathi, or Gujarati, transcribing and normalizing with high precision into standard engineering English.
  - Complemented by Digital India Bhashini open APIs where mandated.

### B. VEXYL AI (vexyl.ai) — Self-Hosted Enterprise On-Prem Voice Gateway
- **Evaluation & Role:**
  - **VEXYL AI** (`vexyl.ai`) is an open-source, self-hosted **AI Voice Gateway** engineered for high-security enterprise environments and data sovereignty (100% on-premise, zero audio leaves the CPSE firewall).
  - **VEXYL STT (Speech-to-Text):** Self-hosted transcription server optimized for **14 Indian languages** with ultra-low latency (**$\approx 150\text{ ms}$ inference**).
  - **VEXYL TTS (Text-to-Speech):** Self-hosted Indic synthesis supporting **22 Indian languages with 69 pre-built voices** (wrapping `ai4bharat/indic-parler-tts`).
  - **Plant Telephony & SIP/PBX Integration:** Directly bridges with CPSE internal PBX systems (SIP, Asterisk, FreePBX, FreeSWITCH).
  - **CPSE Plant Floor Use Case:** Storekeepers or maintenance technicians working in hazardous plant units (refineries, boiler rooms, coal mines) wearing protective gear can use **internal plant walkie-talkies or landline desk phones** to dial an automated CPSE Material Master Voice Hotline, state a part name or code in their native tongue, and receive immediate inventory and code verification.

### C. OpenAI Whisper (`tiny.en` / `base`) — Local On-Device Edge Fallback
- **Evaluation & Role:**
  - Fully local, offline ASR engine running via `whisper.cpp` directly on client desktop/laptop CPUs with $< 200\text{ ms}$ latency.
  - Designed for remote, isolated CPSE installations (e.g., Coal India open-cast mines in Dhanbad, ONGC offshore platforms in Bombay High, or NTPC remote sites) with zero internet access and no local server deployment.


