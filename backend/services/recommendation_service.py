import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Word2Vec, FastText

from backend.config import settings
from backend.services.model_loader import registry
from backend.services.text_processor import clean_text_proper, analyze_query_tokens
from backend.services.vector_search import search_dense_vectors
from backend.schemas.product import ProductItem, RecommendationResponse
from backend.schemas.comparison import (
    ComparisonRow,
    ModelResultColumn,
    MultiModelComparisonResponse,
)

logger = logging.getLogger(__name__)

def get_product_embedding_w2v(text: str, model: Word2Vec, vector_size: int = 100) -> np.ndarray:
    """
    Averages constituent word vectors for words present in the Word2Vec vocabulary.
    Returns zero vector if no words are in vocabulary.
    """
    words = text.split()
    valid_words = [word for word in words if word in model.wv]
    if not valid_words:
        return np.zeros(vector_size, dtype=np.float32)
    return np.mean([model.wv[word] for word in valid_words], axis=0).astype(np.float32)

def get_product_embedding_fasttext(text: str, model: FastText, vector_size: int = 100) -> np.ndarray:
    """
    Generates embedding for text using FastText.
    Leverages subword n-grams for out-of-vocabulary words and typos.
    """
    words = text.split()
    if not words:
        return np.zeros(vector_size, dtype=np.float32)
    word_vectors = [model.wv[word] for word in words]
    return np.mean(word_vectors, axis=0).astype(np.float32)

def search_tfidf(
    query_text: str,
    top_n: int = 12,
    exclude_idx: Optional[int] = None,
    category_filter: Optional[str] = None,
    min_rating: Optional[float] = None
) -> Tuple[List[ProductItem], int]:
    """
    Baseline TF-IDF search using sparse cosine similarity.
    """
    if registry.tfidf_vectorizer is None or registry.tfidf_matrix is None:
        return [], 0

    cleaned = clean_text_proper(query_text)
    if not cleaned:
        return [], 0

    query_vec = registry.tfidf_vectorizer.transform([cleaned])
    scores = cosine_similarity(query_vec, registry.tfidf_matrix).flatten()

    df = registry.catalog_df
    candidate_mask = np.ones(len(scores), dtype=bool)

    if exclude_idx is not None and 0 <= exclude_idx < len(scores):
        candidate_mask[exclude_idx] = False

    if category_filter and category_filter != "all" and "main_category" in df.columns:
        cat_mask = (df["main_category"].str.lower() == category_filter.lower()).to_numpy()
        candidate_mask = candidate_mask & cat_mask

    if min_rating is not None and min_rating > 0:
        rating_mask = (df["rating_num"] >= min_rating).to_numpy()
        candidate_mask = candidate_mask & rating_mask

    candidate_indices = np.where(candidate_mask)[0]
    total_matches = len(candidate_indices)
    if total_matches == 0:
        return [], 0

    candidate_scores = scores[candidate_indices]
    effective_k = min(top_n, total_matches)
    top_sub_idx = np.argpartition(candidate_scores, -effective_k)[-effective_k:]
    sorted_sub_idx = top_sub_idx[np.argsort(-candidate_scores[top_sub_idx])]
    final_indices = candidate_indices[sorted_sub_idx]

    results: List[ProductItem] = []
    for idx in final_indices:
        row = df.iloc[idx]
        sim_score = round(float(scores[idx]), 4)
        img_url = row.get("image")
        if pd_is_null(img_url) or not str(img_url).startswith("http"):
            img_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60"

        raw_rating = row.get("ratings", "N/A")
        rating_str = str(raw_rating) if not pd_is_null(raw_rating) and str(raw_rating).lower() != "nan" else "N/A"

        results.append(
            ProductItem(
                catalog_id=int(idx),
                name=str(row.get("name", "Unknown Product")),
                main_category=str(row.get("main_category", "General")),
                sub_category=str(row.get("sub_category", "General")),
                image=str(img_url),
                link=str(row.get("link", "#")),
                ratings=rating_str,
                rating_num=float(row.get("rating_num", 0.0)),
                no_of_ratings=str(row.get("no_of_ratings", "0")),
                discount_price=str(row.get("discount_price", "N/A")),
                actual_price=str(row.get("actual_price", "N/A")),
                similarity_score=sim_score,
                model_route="TF-IDF Baseline",
            )
        )
    return results, total_matches

def pd_is_null(val: Any) -> bool:
    import pandas as pd
    return pd.isnull(val)

def recommend_products(
    query_text: Optional[str] = None,
    catalog_id: Optional[int] = None,
    top_n: int = 12,
    model_mode: str = "hybrid",
    category_filter: Optional[str] = None,
    min_rating: Optional[float] = None,
    sort_by: str = "similarity"
) -> RecommendationResponse:
    """
    Main recommendation dispatch engine implementing the full Acme Retail pipeline:
    - Primary Model: Word2Vec (Dense Semantic)
    - Fallback Model: FastText (Triggered automatically when OOV words/typos are detected)
    - Baseline: TF-IDF support
    """
    t0 = time.time()
    df = registry.catalog_df
    w2v = registry.word2vec_model
    ft = registry.fasttext_model

    if df is None or w2v is None or ft is None:
        raise RuntimeError("Model registry is not ready.")

    oov_words: List[str] = []
    tokens_list: List[str] = []
    cleaned_query: str = ""
    is_fallback = False
    model_engine = "Word2Vec"
    model_used = "Word2Vec (Primary)"
    exclude_self_idx: Optional[int] = None
    query_display: str = ""

    # Case A: Query by Catalog Product Index (Product-to-Product Similarity)
    if catalog_id is not None:
        if catalog_id < 0 or catalog_id >= len(df):
            raise IndexError(f"Product catalog index {catalog_id} is out of bounds (0 - {len(df)-1}).")

        exclude_self_idx = catalog_id
        target_product = df.iloc[catalog_id]
        query_display = str(target_product.get("name", f"Product #{catalog_id}"))
        cleaned_query = str(target_product.get("cleaned_text", ""))
        tokens_list = cleaned_query.split()

        if model_mode == "fasttext":
            model_engine = "FastText"
            model_used = "FastText (Catalog Product Vector)"
            q_vector = target_product["fasttext_vector"]
            catalog_norm = registry.fasttext_matrix_norm
        else:
            # Word2Vec is primary for catalog index queries
            model_engine = "Word2Vec"
            model_used = "Word2Vec (Catalog Product Vector)"
            q_vector = target_product["w2v_vector"]
            catalog_norm = registry.w2v_matrix_norm

        results, total_matches = search_dense_vectors(
            query_vector=q_vector,
            catalog_matrix_norm=catalog_norm,
            model_route_label=model_engine,
            top_n=top_n,
            exclude_idx=exclude_self_idx,
            category_filter=category_filter,
            min_rating=min_rating,
            sort_by=sort_by
        )

        latency = round((time.time() - t0) * 1000, 2)
        return RecommendationResponse(
            query=query_display,
            query_type="catalog_index",
            cleaned_query=cleaned_query,
            query_tokens=tokens_list,
            model_used=model_used,
            model_engine=model_engine,
            is_fallback_triggered=False,
            oov_words=[],
            total_results=total_matches,
            latency_ms=latency,
            recommendations=results,
        )

    # Case B: Query by Free Plain Text
    if not query_text or not query_text.strip():
        # Empty query: return popular/top products
        query_display = "Featured Products"
        results, total_matches = search_dense_vectors(
            query_vector=registry.w2v_matrix_norm[0],  # sample centroid
            catalog_matrix_norm=registry.w2v_matrix_norm,
            model_route_label="Catalog Featured",
            top_n=top_n,
            exclude_idx=None,
            category_filter=category_filter,
            min_rating=min_rating,
            sort_by="rating"
        )
        latency = round((time.time() - t0) * 1000, 2)
        return RecommendationResponse(
            query="Featured Products",
            query_type="text",
            cleaned_query="",
            query_tokens=[],
            model_used="Catalog Browse",
            model_engine="Word2Vec",
            is_fallback_triggered=False,
            oov_words=[],
            total_results=total_matches,
            latency_ms=latency,
            recommendations=results,
        )

    query_display = query_text.strip()
    analysis = analyze_query_tokens(query_display)
    cleaned_query = analysis["cleaned"]
    tokens_list = analysis["tokens"]

    if not cleaned_query:
        # Fallback if text cleaner removed everything (e.g., all digits/symbols)
        cleaned_query = query_display.lower()
        tokens_list = cleaned_query.split()

    # Detect Out-Of-Vocabulary (OOV) terms for Word2Vec
    vocab_w2v = w2v.wv
    oov_words = [word for word in tokens_list if word not in vocab_w2v]
    oov_ratio = len(oov_words) / len(tokens_list) if len(tokens_list) > 0 else 0.0

    # TF-IDF mode request
    if model_mode == "tfidf":
        model_engine = "TF-IDF"
        model_used = "TF-IDF (Keyword Lexical Baseline)"
        results, total_matches = search_tfidf(
            query_text=cleaned_query,
            top_n=top_n,
            exclude_idx=None,
            category_filter=category_filter,
            min_rating=min_rating
        )
    elif model_mode == "fasttext":
        model_engine = "FastText"
        model_used = "FastText (Manual Override: Subword Embedding)"
        is_fallback = (len(oov_words) > 0)
        q_vector = get_product_embedding_fasttext(cleaned_query, ft)
        results, total_matches = search_dense_vectors(
            query_vector=q_vector,
            catalog_matrix_norm=registry.fasttext_matrix_norm,
            model_route_label="FastText Subword",
            top_n=top_n,
            exclude_idx=None,
            category_filter=category_filter,
            min_rating=min_rating,
            sort_by=sort_by
        )
    elif model_mode == "word2vec":
        model_engine = "Word2Vec"
        model_used = "Word2Vec (Manual Override: Dense Vocabulary)"
        q_vector = get_product_embedding_w2v(cleaned_query, w2v)
        results, total_matches = search_dense_vectors(
            query_vector=q_vector,
            catalog_matrix_norm=registry.w2v_matrix_norm,
            model_route_label="Word2Vec",
            top_n=top_n,
            exclude_idx=None,
            category_filter=category_filter,
            min_rating=min_rating,
            sort_by=sort_by
        )
    else:
        # HYBRID ROUTE (Primary: Word2Vec, Fallback: FastText)
        if oov_ratio > settings.OOV_FALLBACK_THRESHOLD:
            # Fallback triggered!
            is_fallback = True
            model_engine = "FastText"
            model_used = f"FastText Fallback (Triggered: {len(oov_words)} OOV term(s) [{', '.join(oov_words)}])"
            q_vector = get_product_embedding_fasttext(cleaned_query, ft)
            results, total_matches = search_dense_vectors(
                query_vector=q_vector,
                catalog_matrix_norm=registry.fasttext_matrix_norm,
                model_route_label="FastText Fallback",
                top_n=top_n,
                exclude_idx=None,
                category_filter=category_filter,
                min_rating=min_rating,
                sort_by=sort_by
            )
        else:
            # Primary Word2Vec route
            is_fallback = False
            model_engine = "Word2Vec"
            model_used = "Word2Vec (Primary Model: 100% Vocabulary Match)"
            q_vector = get_product_embedding_w2v(cleaned_query, w2v)
            results, total_matches = search_dense_vectors(
                query_vector=q_vector,
                catalog_matrix_norm=registry.w2v_matrix_norm,
                model_route_label="Word2Vec Primary",
                top_n=top_n,
                exclude_idx=None,
                category_filter=category_filter,
                min_rating=min_rating,
                sort_by=sort_by
            )

    latency = round((time.time() - t0) * 1000, 2)
    return RecommendationResponse(
        query=query_display,
        query_type="text",
        cleaned_query=cleaned_query,
        query_tokens=tokens_list,
        model_used=model_used,
        model_engine=model_engine,
        is_fallback_triggered=is_fallback,
        oov_words=oov_words,
        total_results=total_matches,
        latency_ms=latency,
        recommendations=results,
    )

def compare_models_side_by_side(query: str, top_n: int = 5) -> MultiModelComparisonResponse:
    """
    Executes similarity search across TF-IDF, Word2Vec, and FastText models for a given query,
    returning a side-by-side comparison table (Notebook Cell 20).
    """
    t0 = time.time()
    cleaned = clean_text_proper(query)
    tokens = cleaned.split() if cleaned else query.lower().split()
    
    w2v = registry.word2vec_model
    vocab_w2v = w2v.wv if w2v else {}
    oov_words = [w for w in tokens if w not in vocab_w2v]

    # 1. TF-IDF baseline
    tfidf_results, _ = search_tfidf(query_text=query, top_n=top_n)

    # 2. Word2Vec primary
    w2v_vec = get_product_embedding_w2v(cleaned, registry.word2vec_model)
    w2v_results, _ = search_dense_vectors(
        query_vector=w2v_vec,
        catalog_matrix_norm=registry.w2v_matrix_norm,
        model_route_label="Word2Vec",
        top_n=top_n
    )

    # 3. FastText fallback
    ft_vec = get_product_embedding_fasttext(cleaned, registry.fasttext_model)
    ft_results, _ = search_dense_vectors(
        query_vector=ft_vec,
        catalog_matrix_norm=registry.fasttext_matrix_norm,
        model_route_label="FastText",
        top_n=top_n
    )

    rows: List[ComparisonRow] = []
    for rank in range(top_n):
        tf_col = None
        if rank < len(tfidf_results):
            p = tfidf_results[rank]
            tf_col = ModelResultColumn(
                catalog_id=p.catalog_id,
                name=p.name,
                main_category=p.main_category,
                image=p.image,
                similarity_score=p.similarity_score or 0.0,
                price=p.discount_price,
            )

        w2v_col = None
        if rank < len(w2v_results):
            p = w2v_results[rank]
            w2v_col = ModelResultColumn(
                catalog_id=p.catalog_id,
                name=p.name,
                main_category=p.main_category,
                image=p.image,
                similarity_score=p.similarity_score or 0.0,
                price=p.discount_price,
            )

        ft_col = None
        if rank < len(ft_results):
            p = ft_results[rank]
            ft_col = ModelResultColumn(
                catalog_id=p.catalog_id,
                name=p.name,
                main_category=p.main_category,
                image=p.image,
                similarity_score=p.similarity_score or 0.0,
                price=p.discount_price,
            )

        rows.append(ComparisonRow(rank=rank + 1, tfidf=tf_col, word2vec=w2v_col, fasttext=ft_col))

    # Analytical insight generation
    if oov_words:
        insights = (
            f"Out-of-Vocabulary (OOV) terms detected: {oov_words}. "
            "Notice how FastText leverages subword character n-grams to gracefully handle unseen/typo tokens, "
            "whereas Word2Vec defaults to zero for the missing words and TF-IDF fails if exact keyword tokens do not match."
        )
    else:
        insights = (
            "All query tokens are recognized in Word2Vec vocabulary. "
            "Word2Vec delivers high-precision semantic clustering on known e-commerce terminology, "
            "while FastText produces closely correlated embeddings."
        )

    latency = round((time.time() - t0) * 1000, 2)
    return MultiModelComparisonResponse(
        query=query,
        cleaned_query=cleaned,
        oov_words=oov_words,
        latency_ms=latency,
        rows=rows,
        insights=insights,
    )
