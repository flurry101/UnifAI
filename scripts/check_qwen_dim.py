import os
from sentence_transformers import SentenceTransformer

def get_dimension():
    model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    embeddings = model.encode(["test"])
    dim = embeddings.shape[1]
    print(f"QWEN_DIMENSION={dim}")

if __name__ == "__main__":
    get_dimension()
