from typing import List, Optional
from pydantic import BaseModel, Field

class ModelResultColumn(BaseModel):
    catalog_id: int
    name: str
    main_category: str
    image: Optional[str] = None
    similarity_score: float
    price: Optional[str] = None

class ComparisonRow(BaseModel):
    rank: int
    tfidf: Optional[ModelResultColumn] = None
    word2vec: Optional[ModelResultColumn] = None
    fasttext: Optional[ModelResultColumn] = None

class MultiModelComparisonRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query text to compare across all three models")
    top_n: int = Field(5, ge=1, le=20, description="Top-N recommendations to compare side by side")

class MultiModelComparisonResponse(BaseModel):
    query: str
    cleaned_query: str
    oov_words: List[str]
    latency_ms: float
    rows: List[ComparisonRow]
    insights: str
