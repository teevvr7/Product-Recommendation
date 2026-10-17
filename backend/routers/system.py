from fastapi import APIRouter
from typing import Dict, Any
from backend.services.model_loader import registry
from backend.config import settings

router = APIRouter(prefix="/system", tags=["System Diagnostics"])

@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy" if registry.is_ready else "initializing",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ready": registry.is_ready,
    }

@router.get("/stats")
def system_statistics() -> Dict[str, Any]:
    """
    Returns system, model, and vocabulary statistics for technical assessment verification.
    """
    w2v_vocab_size = len(registry.word2vec_model.wv.index_to_key) if registry.word2vec_model else 0
    fasttext_vocab_size = len(registry.fasttext_model.wv.index_to_key) if registry.fasttext_model else 0
    tfidf_vocab_size = len(registry.tfidf_vectorizer.vocabulary_) if registry.tfidf_vectorizer else 0

    return {
        "status": "operational",
        "total_catalog_products": registry.total_products,
        "embedding_dimensions": settings.EMBEDDING_DIM,
        "models": {
            "primary": {
                "name": "Word2Vec",
                "architecture": "Skip-Gram (sg=1)",
                "window": 5,
                "vector_size": 100,
                "vocabulary_size": w2v_vocab_size,
                "role": "Primary semantic recommendation engine for in-vocabulary queries & catalog items",
            },
            "fallback": {
                "name": "FastText",
                "architecture": "Skip-Gram with character n-grams (min_n=3, max_n=6)",
                "window": 5,
                "vector_size": 100,
                "vocabulary_size": fasttext_vocab_size,
                "role": "Automatic fallback engine for queries containing Out-of-Vocabulary (OOV) terms, typos, or slang",
            },
            "baseline": {
                "name": "TF-IDF",
                "ngram_range": "(1, 2)",
                "max_features": 5000,
                "vocabulary_size": tfidf_vocab_size,
                "role": "Baseline keyword model for side-by-side assessment benchmarking",
            }
        },
        "artifacts_load_duration_seconds": registry.load_duration_seconds,
        "total_categories": len(registry.categories),
        "available_categories": registry.categories,
    }
