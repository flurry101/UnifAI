import sys
import os
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.retrieval.vector_store import PostgresVectorStore
from src.retrieval.embeddings import Qwen3EmbeddingProvider
from src.retrieval.indexing import IndexingPipeline
from scripts.dataset.lane5_retrieval_evaluation import get_synthetic_data

def index_synthetic():
    print("Initializing Lane 5 Indexing Pipeline for Synthetic V2...")
    vector_store = PostgresVectorStore()
    embedding_provider = Qwen3EmbeddingProvider()
    pipeline = IndexingPipeline(vector_store, embedding_provider)
    
    records, _ = get_synthetic_data()
    
    batch_size = 64
    print(f"Indexing {len(records)} Synthetic V2 records into Supabase in batches of {batch_size}...")
    
    import time
    start_time = time.time()
    
    for i in tqdm(range(0, len(records), batch_size), desc="Indexing Synthetic Batches"):
        batch = records[i:i + batch_size]
        pipeline.index_records(batch)
        
    duration = time.time() - start_time
    print(f"Indexing Synthetic V2 complete in {duration:.2f} seconds.")

if __name__ == "__main__":
    index_synthetic()
