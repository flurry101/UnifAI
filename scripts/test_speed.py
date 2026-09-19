import time
from sentence_transformers import SentenceTransformer

def test_qwen_speed():
    model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    texts = ["BALL VALVE CARBON STEEL DN100 CLASS 150"] * 64
    start = time.time()
    model.encode(texts)
    print(f"Time for 64 records: {time.time() - start:.2f}s")

if __name__ == "__main__":
    test_qwen_speed()
