-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Create material_retrieval table
CREATE TABLE IF NOT EXISTS material_retrieval (
    material_id TEXT PRIMARY KEY,
    cpse_id TEXT NOT NULL,
    original_material_code TEXT,
    normalized_description TEXT,
    retrieval_representation TEXT,
    embedding VECTOR(1024),
    embedding_model TEXT,
    embedding_version TEXT,
    representation_version TEXT,
    source_type TEXT,
    source_system TEXT,
    source_record_id TEXT,
    source_file TEXT,
    source_row INTEGER,
    ingestion_timestamp TEXT,
    processing_version TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create HNSW index for cosine similarity
CREATE INDEX IF NOT EXISTS material_retrieval_embedding_idx ON material_retrieval USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
