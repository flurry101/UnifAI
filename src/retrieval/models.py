from pydantic import BaseModel, Field
from typing import List, Optional

class Candidate(BaseModel):
    material_id: str
    cpse_id: str
    retrieval_sources: List[str]
    bm25_score: Optional[float] = None
    vector_similarity: Optional[float] = None
    retrieval_rank: Optional[int] = None
    retrieval_version: str
    representation_version: str
    embedding_model: str
    embedding_version: str

class CandidateSet(BaseModel):
    query_material_id: str
    candidates: List[Candidate]
    metadata: Optional[dict] = None

