from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.schemas.product import RecommendationRequest, RecommendationResponse
from backend.services.recommendation_service import recommend_products

router = APIRouter(prefix="/recommend", tags=["Recommendations"])

@router.post("", response_model=RecommendationResponse)
def get_recommendations(req: RecommendationRequest):
    """
    Main recommendation endpoint.
    Accepts plain search text or reference catalog ID.
    Routes to Word2Vec primary model or FastText fallback engine automatically on OOV.
    """
    try:
        response = recommend_products(
            query_text=req.query,
            catalog_id=req.catalog_id,
            top_n=req.top_n,
            model_mode=req.model_mode,
            category_filter=req.category,
            min_rating=req.min_rating,
            sort_by=req.sort_by
        )
        return response
    except IndexError as ie:
        raise HTTPException(status_code=404, detail=str(ie))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation processing error: {str(e)}")

@router.get("/similar/{catalog_id}", response_model=RecommendationResponse)
def get_similar_to_item(
    catalog_id: int,
    top_n: int = Query(12, ge=1, le=50),
    model_mode: str = Query("hybrid", regex="^(hybrid|word2vec|fasttext|tfidf)$"),
    category: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0),
    sort_by: str = Query("similarity")
):
    """
    Convenience endpoint for product-to-product semantic similarity by catalog ID.
    Excludes the queried item itself and ranks catalog by cosine similarity.
    """
    try:
        response = recommend_products(
            query_text=None,
            catalog_id=catalog_id,
            top_n=top_n,
            model_mode=model_mode,
            category_filter=category,
            min_rating=min_rating,
            sort_by=sort_by
        )
        return response
    except IndexError as ie:
        raise HTTPException(status_code=404, detail=str(ie))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
