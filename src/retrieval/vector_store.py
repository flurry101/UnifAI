import os
import psycopg
from typing import List, Dict, Any, Tuple
from pgvector.psycopg import register_vector

class VectorStore:
    def upsert(self, records: List[Dict[str, Any]]):
        raise NotImplementedError
        
    def search(self, query_embedding: List[float], top_k: int = 50, exclude_material_id: str = None) -> List[Tuple[str, float]]:
        raise NotImplementedError
        
    def get_all_materials(self) -> List[Dict[str, Any]]:
        raise NotImplementedError


class PostgresVectorStore(VectorStore):
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set")
            
    def _get_connection(self):
        conn = psycopg.connect(self.db_url)
        register_vector(conn)
        return conn

    def upsert(self, records: List[Dict[str, Any]]):
        if not records:
            return
            
        upsert_query = """
            INSERT INTO material_retrieval (
                material_id, cpse_id, original_material_code, normalized_description, 
                retrieval_representation, embedding, embedding_model, embedding_version, 
                representation_version, source_type, source_system, source_record_id, 
                source_file, source_row, ingestion_timestamp, processing_version
            ) VALUES (
                %(material_id)s, %(cpse_id)s, %(original_material_code)s, %(normalized_description)s,
                %(retrieval_representation)s, %(embedding)s, %(embedding_model)s, %(embedding_version)s,
                %(representation_version)s, %(source_type)s, %(source_system)s, %(source_record_id)s,
                %(source_file)s, %(source_row)s, %(ingestion_timestamp)s, %(processing_version)s
            )
            ON CONFLICT (material_id) DO UPDATE SET
                cpse_id = EXCLUDED.cpse_id,
                original_material_code = EXCLUDED.original_material_code,
                normalized_description = EXCLUDED.normalized_description,
                retrieval_representation = EXCLUDED.retrieval_representation,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model,
                embedding_version = EXCLUDED.embedding_version,
                representation_version = EXCLUDED.representation_version,
                source_type = EXCLUDED.source_type,
                source_system = EXCLUDED.source_system,
                source_record_id = EXCLUDED.source_record_id,
                source_file = EXCLUDED.source_file,
                source_row = EXCLUDED.source_row,
                ingestion_timestamp = EXCLUDED.ingestion_timestamp,
                processing_version = EXCLUDED.processing_version,
                updated_at = CURRENT_TIMESTAMP
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(upsert_query, records)
            conn.commit()

    def search(self, query_embedding: List[float], top_k: int = 50, exclude_material_id: str = None) -> List[Tuple[str, float]]:
        # Use cosine distance operator '<=>' for pgvector
        search_query = """
            SELECT material_id, 1 - (embedding <=> %(embedding)s::vector) AS similarity
            FROM material_retrieval
            WHERE material_id != %(exclude_id)s
            ORDER BY embedding <=> %(embedding)s::vector
            LIMIT %(top_k)s
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(search_query, {
                    "embedding": query_embedding, 
                    "exclude_id": exclude_material_id if exclude_material_id else "",
                    "top_k": top_k
                })
                results = cur.fetchall()
                
        return [(row[0], float(row[1])) for row in results]

    def get_all_materials(self) -> List[Dict[str, Any]]:
        """Used to fetch the corpus for LexicalRetriever."""
        query = """
            SELECT material_id, cpse_id, retrieval_representation 
            FROM material_retrieval
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()
                
        return [
            {
                "material_id": row[0],
                "cpse_id": row[1],
                "text": row[2]
            }
            for row in results
        ]
