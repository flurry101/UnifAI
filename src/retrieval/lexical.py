from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
import numpy as np

class LexicalRetriever:
    def refresh(self, corpus: List[Dict[str, Any]]):
        raise NotImplementedError

    def search(self, query_text: str, top_k: int = 50) -> List[Tuple[str, float]]:
        raise NotImplementedError

class BM25Retriever(LexicalRetriever):
    def __init__(self):
        self.bm25 = None
        self.corpus_records = []
        
    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        return text.lower().split()

    def refresh(self, corpus: List[Dict[str, Any]]):
        """
        Builds the BM25 index from a list of records.
        corpus should contain dicts with 'material_id' and 'text'.
        """
        self.corpus_records = corpus
        tokenized_corpus = [self._tokenize(doc['text']) for doc in corpus]
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)
        else:
            self.bm25 = None

    def search(self, query_text: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Returns a list of (material_id, score) tuples.
        """
        if not self.bm25 or not query_text:
            return []
            
        tokenized_query = self._tokenize(query_text)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top_k indices
        top_n = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_n:
            score = scores[idx]
            if score > 0:
                results.append((self.corpus_records[idx]['material_id'], float(score)))
                
        return results
