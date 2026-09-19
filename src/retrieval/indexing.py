from typing import List
from src.ingestion.unified_schema import UnifiedMaterialRecord
from src.retrieval.representation import RetrievalRepresentationBuilder
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.vector_store import VectorStore

class IndexingPipeline:
    def __init__(self, vector_store: VectorStore, embedding_provider: EmbeddingProvider):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.rep_builder = RetrievalRepresentationBuilder()
        
        # Pre-load existing representations for incremental checks
        self.existing_records = {
            m["material_id"]: m["text"] for m in self.vector_store.get_all_materials()
        }

    def index_records(self, records: List[UnifiedMaterialRecord]) -> dict:
        """
        Indexes a batch of records, skipping those whose retrieval_representation is unchanged.
        Returns metrics for the batch.
        """
        metrics = {"skipped": 0, "embedded": 0, "failed": 0}
        
        records_to_embed = []
        texts_to_encode = []
        
        # 1. Check which records actually need embedding
        for r in records:
            try:
                rep_text = self.rep_builder.build(r)
                mat_id = r.provenance.source_record_id
                
                if mat_id in self.existing_records and self.existing_records[mat_id] == rep_text:
                    metrics["skipped"] += 1
                else:
                    records_to_embed.append((r, rep_text))
                    texts_to_encode.append(rep_text)
            except Exception:
                metrics["failed"] += 1
                
        if not records_to_embed:
            return metrics
            
        # 2. Embed only the new/changed records
        try:
            embeddings = self.embedding_provider.encode(texts_to_encode)
            db_records = []
            
            for i, (r, rep_text) in enumerate(records_to_embed):
                prov = r.provenance
                db_records.append({
                    "material_id": prov.source_record_id,
                    "cpse_id": r.cpse,
                    "original_material_code": r.original_material_code,
                    "normalized_description": r.normalized_description,
                    "retrieval_representation": rep_text,
                    "embedding": embeddings[i],
                    "embedding_model": "Qwen3-Embedding-0.6B",
                    "embedding_version": "1.0",
                    "representation_version": "1.0",
                    "source_type": prov.source_type,
                    "source_system": prov.source_system,
                    "source_record_id": prov.source_record_id,
                    "source_file": prov.source_file,
                    "source_row": prov.source_row,
                    "ingestion_timestamp": prov.ingestion_timestamp,
                    "processing_version": prov.processing_version
                })
                
            self.vector_store.upsert(db_records)
            metrics["embedded"] += len(db_records)
            
            # Update local cache so we don't re-embed if passed again in same session
            for m in db_records:
                self.existing_records[m["material_id"]] = m["retrieval_representation"]
                
        except Exception:
            metrics["failed"] += len(records_to_embed)
            
        return metrics
