from typing import List
from sentence_transformers import SentenceTransformer

class EmbeddingProvider:
    def get_dimension(self) -> int:
        raise NotImplementedError
        
    def encode(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

class Qwen3EmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        self.model_name = "Qwen/Qwen3-Embedding-0.6B"
        # Let it fail loudly if model can't be loaded
        self.model = SentenceTransformer(self.model_name)
        
    def get_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
        
    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
