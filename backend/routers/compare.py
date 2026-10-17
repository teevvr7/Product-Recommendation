from fastapi import APIRouter, HTTPException
from backend.schemas.comparison import (
    MultiModelComparisonRequest,
    MultiModelComparisonResponse,
)
from backend.services.recommendation_service import compare_models_side_by_side

router = APIRouter(prefix="/compare", tags=["Multi-Model Comparison"])

@router.post("", response_model=MultiModelComparisonResponse)
def compare_models(req: MultiModelComparisonRequest):
    """
    Executes similarity search simultaneously across:
    1. TF-IDF (Baseline Lexical)
    2. Word2Vec (Primary Dense Semantic)
    3. FastText (Fallback Subword Semantic)
    
    Returns a unified side-by-side comparison table to evaluate behavior on known words vs typos/OOV.
    """
    try:
        response = compare_models_side_by_side(query=req.query, top_n=req.top_n)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison evaluation failed: {str(e)}")
