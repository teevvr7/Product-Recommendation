import os
from pathlib import Path
from pydantic import BaseModel

# Base directory is the root Product-Recommendation folder
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    # Application Info
    APP_NAME: str = "Acme Retail Semantic Recommendation System"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "Production-grade e-commerce semantic search and recommendation engine with Word2Vec primary and FastText fallback."
    
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Modular Directories
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    MODELS_DIR: Path = BASE_DIR / "models"
    NOTEBOOKS_DIR: Path = BASE_DIR / "notebooks"
    DOCS_DIR: Path = BASE_DIR / "docs"
    
    # File Paths (Modular locations with fallback)
    CATALOG_ENRICHED_PATH: Path = PROCESSED_DATA_DIR / "catalog_enriched.pkl"
    ORIGINAL_CATALOG_PKL: Path = PROCESSED_DATA_DIR / "product_catalog_vectorized.pkl"
    ACME_CSV_PATH: Path = RAW_DATA_DIR / "AcmeRetail_Products_70000.csv"
    AMAZON_CSV_PATH: Path = RAW_DATA_DIR / "Amazon-Products.csv"
    
    WORD2VEC_MODEL_PATH: Path = MODELS_DIR / "word2vec_model.model"
    FASTTEXT_MODEL_PATH: Path = MODELS_DIR / "fasttext_model.model"
    TFIDF_MODEL_PATH: Path = MODELS_DIR / "tfidf_vectorizer.pkl"
    TFIDF_MATRIX_PATH: Path = MODELS_DIR / "tfidf_matrix.pkl"
    
    # Frontend directory
    FRONTEND_DIR: Path = BASE_DIR / "frontend"
    STATIC_DIR: Path = BASE_DIR / "frontend" / "static"
    
    # Model & Recommendation Parameters
    DEFAULT_TOP_N: int = 12
    MAX_TOP_N: int = 50
    EMBEDDING_DIM: int = 100
    OOV_FALLBACK_THRESHOLD: float = 0.0  # If OOV ratio > 0.0, fallback to FastText

settings = Settings()
