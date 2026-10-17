from typing import List, Optional
from pydantic import BaseModel, Field

class ProductItem(BaseModel):
    catalog_id: int
    name: str
    main_category: str
    sub_category: str
    image: Optional[str] = None
    link: Optional[str] = None
    ratings: Optional[str] = "N/A"
    rating_num: float = 0.0
    no_of_ratings: Optional[str] = "0"
    discount_price: Optional[str] = "N/A"
    actual_price: Optional[str] = "N/A"
    similarity_score: Optional[float] = None
    model_route: Optional[str] = None

class ProductDetail(ProductItem):
    combined_raw_text: Optional[str] = ""
    cleaned_text: Optional[str] = ""
    vector_preview: Optional[List[float]] = None

class RecommendationRequest(BaseModel):
    query: Optional[str] = Field(None, description="Free text search query (e.g. 'wireless mouse', 'cotton shirt')")
    catalog_id: Optional[int] = Field(None, description="Catalog index of a reference product for product-to-product similarity")
    top_n: int = Field(12, ge=1, le=50, description="Number of recommendations to return")
    model_mode: str = Field("hybrid", description="Recommendation engine mode: 'hybrid', 'word2vec', 'fasttext', 'tfidf'")
    category: Optional[str] = Field(None, description="Optional main category filter (e.g. 'appliances', 'electronics')")
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Minimum star rating filter")
    sort_by: str = Field("similarity", description="Sorting criteria: 'similarity', 'rating', 'price_asc', 'price_desc'")

class RecommendationResponse(BaseModel):
    query: str
    query_type: str  # 'text' or 'catalog_index'
    cleaned_query: Optional[str] = None
    query_tokens: List[str] = []
    model_used: str
    model_engine: str  # 'Word2Vec', 'FastText', or 'TF-IDF'
    is_fallback_triggered: bool = False
    oov_words: List[str] = []
    total_results: int
    latency_ms: float
    recommendations: List[ProductItem]

class CatalogBrowseResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ProductItem]
