# UnifAI Frontend Integration Guide

Welcome to the UnifAI backend! This repository contains the complete AI matching pipeline and the FastAPI backend service.

As a frontend developer, you do **not** need to run any of the ML model training scripts or worry about how the vector database works. The backend abstracts all of the AI logic behind a clean set of REST APIs.

## 1. Setup Instructions

To get the backend running locally on your machine:

1. **Clone the repository**
2. **Set up the virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure your environment:**
   - Copy `.env.example` to `.env`
   - Fill in the `DATABASE_URL` for the Supabase database. (Ask the backend team for the credentials).
   
## 2. The AI Models

The backend relies on two AI models, but they are handled completely differently:

1. **Qwen Embedding Model:**
   - You do **not** need to download this manually.
   - The first time you start the server or run a matching query, the `Qwen/Qwen3-Embedding-0.6B` model will be automatically downloaded and cached from Hugging Face. (Note: The first run might take a minute or two).

2. **The Relationship Classifier (Machine Learning Artifact):**
   - We trained a custom LightGBM model to predict the relationships (Identical, Equivalent, Variant, Distinct).
   - This model is deployed as a `.txt` file and is tracked in the repository.
   - It is located at `artifacts/matching_model/lgb_model.txt`. Ensure this folder exists and contains the model and `metadata.json` before running the backend.

## 3. Starting the Server

Run the FastAPI server locally:

```bash
# On Windows
$env:PYTHONPATH="."
.venv\Scripts\uvicorn app.main:app --reload

# On Mac/Linux
PYTHONPATH="." .venv/bin/uvicorn app.main:app --reload
```

## 4. API Documentation (Your Main Resource)

Once the server is running, navigate to:

👉 **http://localhost:8000/docs**

This Swagger UI provides interactive documentation for all the endpoints you will need to build the dashboard.

### Key API Concepts:

- **Authentication:** Use `POST /api/v1/auth/login` to get a JWT token. Pass this token in the `Authorization: Bearer <token>` header for all other requests.
- **Triggering the AI:** Use `POST /api/v1/materials/{id}/matches` to run the AI pipeline on a specific CPSE material. The backend will return a list of recommended matches (`MatchProposal` objects).
- **Governance:** Use `POST /api/v1/governance/proposals/{id}/decision` to allow an admin to APPROVE or REJECT a match. If approved, the backend automatically creates the official CPSE-to-CNMC linkage.

*For detailed architectural rules and data models, refer to `docs/API_CONTRACT.md`.*
