# UnifAI Codebase & Backend Architecture Analysis

This document provides a comprehensive analysis of the existing UnifAI (SIH26099) repository to serve as the foundation for the final product's backend architecture.

## 1. Existing Architecture & Modules

The current repository implements a highly modular Machine Learning pipeline designed for offline batch processing and evaluation. The core directories are:
- `src/ingestion/`: Handles `UnifiedMaterialRecord` schemas.
- `src/preprocessing/`: Normalization logic.
- `src/extraction/`: NLP / rule-based extraction of technical attributes.
- `src/fingerprint/`: Hashing/deduplication heuristics.
- `src/retrieval/`: Handles indexing and vector search (Lane 5) returning `CandidateSet`.
- `src/matching/`: The core of the harmonization logic. Contains `lane6_features.py` (Pair Feature Generator), Lane 7 ML models, and `lane8_decision.py` (Deterministic Safety Engine).
- `src/ml/`: Training and validation scripts for LightGBM.
- `app/`: Currently houses the `annotation_ui.py` (Streamlit Human Governance UI).

## 2. Existing Data Structures

The system already defines robust, production-ready schemas for the ML pipeline:
- **`UnifiedMaterialRecord`** (Pydantic): The core representation of a material.
- **`CandidateSet` & `Candidate`** (Pydantic): Defines retrieval results.
- **`PairFeatureResult`** (Dataclass): The comparison metrics from Lane 6.
- **`Lane8Decision`** (Dataclass): The final routing object containing `final_relation`, `decision_status` (PROPOSED/REVIEW), confidence, and safety rules triggered.

## 3. Data Flow Trace

```text
Raw CPSE Material
        ↓ (Lanes 1-4) 
UnifiedMaterialRecord 
        ↓ (Lane 5)
Vector Search (Qwen3) & BM25 → CandidateSet
        ↓ (Lane 6)
PairFeatureResult 
        ↓ (Lane 7)
LightGBM Probabilities
        ↓ (Lane 8)
Lane8Decision (Status: PROPOSED or REVIEW)
        ↓
MatchProposal (Backend Persistence)
        ↓
Human Governance (Review / Approval)
        ↓
CNMC + CPSE Mapping
```

## 4. Proposed Product Domain Model

To support a live CPSE-facing web application without duplicating ML logic, the backend implements the following persistent entities:

1. **`User`**: (Persistent) CPSE engineers, Technical Reviewers, Admins.
2. **`CPSE`**: (Persistent) Tenant context (e.g., IOCL, BPCL).
3. **`MaterialMaster`**: (Persistent) The raw `UnifiedMaterialRecord` ingested from the CPSE ERP.
4. **`MatchProposal`**: (Persistent) The absolute bridge between the AI Pipeline and Governance. Stores the exact `Lane8Decision`, probabilities, and status (PROPOSED/REVIEW).
5. **`CNMC (Recommended Common National Material Code)`**: (Persistent) A system-generated recommended common material representation created from human-approved harmonization decisions.
6. **`CPSE_CNMC_Mapping`**: (Persistent) The approved linkage between a CPSE's local material code and a CNMC.
7. **`AuditEvent`**: (Persistent) Strict lineage tracking.

## 5. CNMC & CPSE Mapping Design

### What is a CNMC?
The **Recommended Common National Material Code (CNMC)** is NOT an official government mandate, but a system-generated unified representation. 
- **Standardized Description**: Derived from the most complete normalized description among its mapped CPSE items.
- **Technical Attributes**: The intersection of non-conflicting technical attributes.

### Mapping Structure
The architecture preserves the original CPSE code perfectly. 
Mappings only occur after a `MatchProposal` is `APPROVED` by human governance. 

## 6. Governance Workflow

The crucial governance boundary is separating AI Recommendations from Official System State:
```text
AI → Lane 8 → PROPOSED/REVIEW → Human Decision → APPROVED → CNMC/Mapping
```
A `PROPOSED` output from Lane 8 **does not automatically create a mapping**. It creates a `MatchProposal` that can be fast-tracked to `APPROVED` by a governance rule or explicit human action.

A `VARIANT_OF` or `DISTINCT` human decision results in the `MatchProposal` being `REJECTED` for CNMC merging, explicitly preventing unauthorized combinations.

## 7. Model Artifact / Deployment Requirements
- **Qwen3-Embedding-0.6B**: Loaded dynamically via HuggingFace `sentence-transformers`.
- **LightGBM Lane 7 Model**: MUST be serialized to `artifacts/matching_model/lightgbm_model.txt` alongside `feature_schema.json`.
- **FastAPI Orchestration**: FastAPI routes will NOT contain ML logic. They will call Application Services, which in turn orchestrate the frozen Lane 1-8 pipeline.
