import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from gensim.models import Word2Vec, FastText
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix

from backend.config import settings

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Central in-memory state for ML models, vector indices, and product catalog metadata.
    Loaded once at server startup to ensure sub-10ms query execution.
    """
    def __init__(self):
        self.catalog_df: Optional[pd.DataFrame] = None
        self.word2vec_model: Optional[Word2Vec] = None
        self.fasttext_model: Optional[FastText] = None
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[csr_matrix] = None
        
        # Precomputed L2-normalized dense matrices for fast dot-product cosine similarity
        self.w2v_matrix_norm: Optional[np.ndarray] = None
        self.fasttext_matrix_norm: Optional[np.ndarray] = None
        
        # Metadata caches
        self.categories: List[str] = []
        self.category_counts: Dict[str, int] = {}
        self.total_products: int = 0
        self.load_duration_seconds: float = 0.0
        self.is_ready: bool = False

    def _resolve_path(self, primary: Path, fallback_name: str) -> Path:
        if primary.exists():
            return primary
        fallback = settings.BASE_DIR / fallback_name
        if fallback.exists():
            return fallback
        return primary

    def load_artifacts(self):
        t0 = time.time()
        logger.info("[STARTUP] Initializing ModelRegistry and loading pre-trained artifacts from modular directories...")
        
        catalog_path = self._resolve_path(settings.CATALOG_ENRICHED_PATH, "catalog_enriched.pkl")
        orig_catalog_path = self._resolve_path(settings.ORIGINAL_CATALOG_PKL, "product_catalog_vectorized.pkl")
        acme_csv_path = self._resolve_path(settings.ACME_CSV_PATH, "AcmeRetail_Products_70000.csv")

        # 1. Load Enriched Catalog
        if catalog_path.exists():
            logger.info(f"Loading enriched catalog from {catalog_path}...")
            self.catalog_df = joblib.load(catalog_path)
        elif orig_catalog_path.exists():
            logger.info(f"Loading original catalog from {orig_catalog_path} and merging metadata...")
            df = joblib.load(orig_catalog_path)
            if acme_csv_path.exists():
                acme = pd.read_csv(acme_csv_path, usecols=['name', 'image', 'link'])
                acme = acme.drop_duplicates(subset=['name'], keep='first')
                df = df.merge(acme[['name', 'image', 'link']], on='name', how='left')
            df['catalog_id'] = np.arange(len(df))
            self.catalog_df = df
        else:
            raise FileNotFoundError(f"Product catalog vector artifact could not be found at {catalog_path}.")

        # Ensure catalog_id exists
        if 'catalog_id' not in self.catalog_df.columns:
            self.catalog_df['catalog_id'] = np.arange(len(self.catalog_df))

        self.total_products = len(self.catalog_df)
        logger.info(f"Loaded {self.total_products} products into catalog memory.")

        # 2. Load Word2Vec Model (Primary)
        w2v_path = self._resolve_path(settings.WORD2VEC_MODEL_PATH, "word2vec_model.model")
        if w2v_path.exists():
            logger.info(f"Loading Word2Vec model from {w2v_path}...")
            self.word2vec_model = Word2Vec.load(str(w2v_path))
            logger.info(f"Word2Vec vocabulary size: {len(self.word2vec_model.wv.index_to_key)}")
        else:
            raise FileNotFoundError(f"Word2Vec model not found at {w2v_path}")

        # 3. Load FastText Model (Fallback)
        ft_path = self._resolve_path(settings.FASTTEXT_MODEL_PATH, "fasttext_model.model")
        if ft_path.exists():
            logger.info(f"Loading FastText model from {ft_path}...")
            self.fasttext_model = FastText.load(str(ft_path))
            logger.info(f"FastText vocabulary size: {len(self.fasttext_model.wv.index_to_key)}")
        else:
            raise FileNotFoundError(f"FastText model not found at {ft_path}")

        # 4. Load TF-IDF Baseline
        tfidf_path = self._resolve_path(settings.TFIDF_MODEL_PATH, "tfidf_vectorizer.pkl")
        tfidf_mat_path = self._resolve_path(settings.TFIDF_MATRIX_PATH, "tfidf_matrix.pkl")
        if tfidf_path.exists():
            logger.info(f"Loading TF-IDF vectorizer from {tfidf_path}...")
            self.tfidf_vectorizer = joblib.load(tfidf_path)
            
            if tfidf_mat_path.exists():
                self.tfidf_matrix = joblib.load(tfidf_mat_path)
            else:
                logger.info("Computing TF-IDF matrix...")
                self.tfidf_matrix = self.tfidf_vectorizer.transform(self.catalog_df['cleaned_text'])
                joblib.dump(self.tfidf_matrix, tfidf_mat_path)
            logger.info(f"TF-IDF matrix shape: {self.tfidf_matrix.shape}")

        # 5. Pre-stack and L2-normalize dense matrices for instant cosine dot-products
        logger.info("Pre-normalizing Word2Vec catalog matrix...")
        w2v_raw = np.vstack(self.catalog_df['w2v_vector'].values).astype(np.float32)
        w2v_norms = np.linalg.norm(w2v_raw, axis=1, keepdims=True)
        w2v_norms[w2v_norms == 0] = 1e-10
        self.w2v_matrix_norm = w2v_raw / w2v_norms

        logger.info("Pre-normalizing FastText catalog matrix...")
        ft_raw = np.vstack(self.catalog_df['fasttext_vector'].values).astype(np.float32)
        ft_norms = np.linalg.norm(ft_raw, axis=1, keepdims=True)
        ft_norms[ft_norms == 0] = 1e-10
        self.fasttext_matrix_norm = ft_raw / ft_norms

        # 6. Cache unique categories
        if 'main_category' in self.catalog_df.columns:
            cat_series = self.catalog_df['main_category'].dropna()
            self.categories = sorted(cat_series.unique().tolist())
            self.category_counts = cat_series.value_counts().to_dict()

        self.load_duration_seconds = round(time.time() - t0, 2)
        self.is_ready = True
        logger.info(f"[READY] All models & indices loaded in {self.load_duration_seconds}s!")

# Global singleton instance
registry = ModelRegistry()
