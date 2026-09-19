# UnifAI API Contract

This document outlines the API endpoints required to orchestrate the UnifAI Machine Learning pipeline and serve the frontend product.

## 1. Authentication & Roles
- Roles scope data access by CPSE. 
- Roles: `CPSE_USER`, `TECHNICAL_REVIEWER`, `CPSE_ADMIN`, `NATIONAL_ADMIN`, `AUDITOR`.

### `POST /api/v1/auth/login`
- **Purpose**: Authenticate users.
- **Response**: `{"access_token": "str", "role": "str", "cpse_id": "str"}`

## 2. Materials (Ingestion & Search)

### `GET /api/v1/materials`
- **Purpose**: Search the material master.
- **Query Params**: `cpse_id`, `material_code`, `search`, `commodity_class`

### `GET /api/v1/materials/{material_id}`
- **Purpose**: Retrieve full details of a specific material.

### `POST /api/v1/materials`
- **Purpose**: Ingest a new material from a CPSE.
- **AI Pipeline**: Orchestrates Lane 1 → 4, persists to DB, then dispatches for Lane 5 indexing.

## 3. Matching (AI Pipeline Orchestration)

### `POST /api/v1/materials/{material_id}/matches`
- **Purpose**: Executes the ML pipeline to find candidates and generate MatchProposals.
- **AI Pipeline**: Lane 5 → Lane 6 → Lane 7 → Lane 8.
- **Side Effect**: Generates `MatchProposal` records. Does NOT create CNMC mappings.
- **Response**: List of `MatchProposals`.

### `GET /api/v1/materials/{material_id}/matches`
- **Purpose**: Fetch existing `MatchProposals` for a material without re-running the AI.

## 4. Human Governance (Review Queue)

### `GET /api/v1/reviews`
- **Purpose**: Fetches pending `MatchProposals` routed for REVIEW or pending PROPOSED approval.
- **Role**: `TECHNICAL_REVIEWER`, `NATIONAL_ADMIN`

### `POST /api/v1/reviews/{proposal_id}/decision`
- **Purpose**: Records the ground-truth human decision.
- **Request**:
```json
{
  "relationship": "EQUIVALENT", 
  "evidence_types": ["TECHNICAL_CONFLICT"],
  "notes": "Different operational locations."
}
```
- **Side Effect**: Updates `MatchProposal` to APPROVED/REJECTED. If APPROVED for IDENTICAL/EQUIVALENT, orchestrates the creation/update of a CNMC and `CPSE_CNMC_Mapping`.

## 5. Common Material Master (CNMC) & Mapping

### `GET /api/v1/cnmc`
- **Purpose**: Search the global catalog of Recommended Common National Material Codes.

### `GET /api/v1/cnmc/{cnmc_id}`
- **Purpose**: Get detailed lineage of a CNMC.

### `GET /api/v1/mappings`
- **Purpose**: Query approved CPSE → CNMC mappings.

### `GET /api/v1/materials/{material_id}/mapping`
- **Purpose**: Find which CNMC a specific CPSE material is officially mapped to.

## 6. Audit & Traceability

### `GET /api/v1/audit/{entity_id}`
- **Purpose**: Fetch the immutable history of an entity (e.g., how an AI Proposal became an Approved Mapping).
- **Response**: List of events containing actor, action, timestamp, old state, new state, and model version.
