# UnifAI Database Design

This schema implements the strict boundary between AI Recommendations and Human Governance.

## 1. Core Tables

### `cpse_tenant`
- **id**: UUID (PK)
- **code**: VARCHAR (e.g., "IOCL")
- **name**: VARCHAR

### `users`
- **id**: UUID (PK)
- **cpse_id**: UUID (FK)
- **username**: VARCHAR
- **role**: ENUM ('CPSE_USER', 'TECHNICAL_REVIEWER', 'NATIONAL_ADMIN', 'AUDITOR')

### `material_master`
- **id**: UUID (PK)
- **cpse_id**: UUID (FK)
- **original_material_code**: VARCHAR
- **original_description**: TEXT
- **normalized_description**: TEXT
- **attributes_json**: JSONB (Stores Lane 3 extraction results)
- **embedding**: VECTOR (Lane 5 pgvector storage)
- *Purpose*: The raw CPSE catalog. 

## 2. AI Proposal Layer

### `match_proposal`
- **id**: UUID (PK)
- **query_material_id**: UUID (FK to material_master)
- **candidate_material_id**: UUID (FK to material_master)
- **predicted_relation**: ENUM ('IDENTICAL', 'EQUIVALENT', 'VARIANT_OF', 'DISTINCT', 'UNDETERMINED')
- **confidence_level**: VARCHAR ('HIGH', 'MEDIUM', 'LOW', 'REVIEW')
- **decision_status**: ENUM ('PROPOSED', 'REVIEW')
- **lane7_probabilities**: JSONB
- **lane8_decision**: JSONB
- **governance_state**: ENUM ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED')
- **model_version**: VARCHAR
- **created_at**: TIMESTAMP
- *Purpose*: The bridge between the AI Pipeline and Human Governance. Provides full traceability.

## 3. Governance & Harmonization

### `cnmc_registry` 
- **id**: UUID (PK)
- **cnmc_code**: VARCHAR (e.g., "CNMC-100234")
- **standardized_description**: TEXT
- **core_attributes**: JSONB
- **status**: ENUM ('PROPOSED', 'APPROVED')
- **created_at**: TIMESTAMP
- *Purpose*: The Recommended Common National Material Code.

### `cpse_cnmc_mapping`
- **id**: UUID (PK)
- **cpse_material_id**: UUID (FK to material_master)
- **cnmc_id**: UUID (FK to cnmc_registry)
- **relationship_type**: ENUM ('IDENTICAL', 'EQUIVALENT')
- **match_proposal_id**: UUID (FK to match_proposal, for traceability)
- *Purpose*: The official linkage. Only created when a MatchProposal is APPROVED.

## 4. Audit & Lineage

### `audit_logs`
- **id**: UUID (PK)
- **entity_name**: VARCHAR (e.g., "MATCH_PROPOSAL", "CPSE_CNMC_MAPPING")
- **entity_id**: UUID
- **actor_id**: UUID (Nullable, System if AI)
- **action**: VARCHAR (e.g., "AI_PROPOSED", "HUMAN_APPROVED")
- **previous_state**: JSONB
- **new_state**: JSONB
- **timestamp**: TIMESTAMP
