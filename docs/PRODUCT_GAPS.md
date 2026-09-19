# UnifAI Product Gaps Analysis

This document outlines the gap between the frozen ML pipeline (Lanes 1-8) and the requirements of the final SIH26099 Web Application prototype.

## ALREADY EXISTS
- **AI Pipeline (Lanes 1-8)**: The entire core harmonization logic is robust, tested, and strictly orchestrated.
- **Data Schemas (Internal)**: `UnifiedMaterialRecord`, `CandidateSet`, `Lane8Decision`.
- **Vector Storage**: Lane 5 `pgvector` indexing architecture.

## PARTIALLY EXISTS
- **Model Persistence**: LightGBM is trained dynamically via scripts. 
  - *Gap*: Needs a dedicated export script (`train_and_save_lane7.py`) to save `.txt` artifacts for fast API loading.
- **Human Governance UI**: The Streamlit app exists locally, but the workflow must be migrated to the persistent API via `MatchProposal` records.

## MISSING (Required for Backend)
- **Service Orchestration Layer**: FastAPI routes must delegate to internal services that cleanly call the frozen Lanes 1-8 without duplicating ML logic.
- **MatchProposal Persistence**: The critical missing DB entity that bridges the gap between Lane 8 AI output and Human Governance Action.
- **API Endpoints**: Comprehensive Search, Mapping, and Audit APIs.
- **Authentication/Roles**: CPSE-scoped roles (e.g., CPSE_USER vs TECHNICAL_REVIEWER).
- **Persistent RDBMS Schema**: PostgreSQL tables for `cnmc_registry`, `cpse_cnmc_mapping`, and `match_proposal`.

## SAP / ERP BOUNDARY
The backend must not pretend to have live SAP RFC connections. Instead, the API will expose mock import/export API endpoints to simulate asynchronous ERP syncing, clearly delineating the prototype's boundaries.
