import re
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
from backend.schemas.product import ProductItem
from backend.services.model_loader import registry

def parse_price_to_numeric(price_str: Optional[str]) -> float:
    """Extract numeric price for sorting purposes."""
    if not price_str or not isinstance(price_str, str):
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", price_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def search_dense_vectors(
    query_vector: np.ndarray,
    catalog_matrix_norm: np.ndarray,
    model_route_label: str,
    top_n: int = 12,
    exclude_idx: Optional[int] = None,
    category_filter: Optional[str] = None,
    min_rating: Optional[float] = None,
    sort_by: str = "similarity"
) -> Tuple[List[ProductItem], int]:
    """
    Performs vector similarity search via L2-normalized dot product.
    Returns ranked ProductItem objects and the total candidates count.
    """
    df = registry.catalog_df
    if df is None or catalog_matrix_norm is None:
        raise RuntimeError("Model registry is not initialized.")

    # 1. Normalize query vector
    q_vec = np.array(query_vector, dtype=np.float32).reshape(-1)
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        # All-zero query vector
        return [], 0
    q_norm_vec = (q_vec / q_norm).reshape(1, -1)

    # 2. Compute Cosine Similarity via fast dot product
    similarity_scores = np.dot(catalog_matrix_norm, q_norm_vec.T).flatten()

    # 3. Apply optional filters
    candidate_mask = np.ones(len(similarity_scores), dtype=bool)

    if exclude_idx is not None and 0 <= exclude_idx < len(similarity_scores):
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

    candidate_scores = similarity_scores[candidate_indices]

    # 4. Sorting & Top-N Selection
    if sort_by == "similarity":
        # Partition top candidates then sort
        effective_k = min(top_n * 3, total_matches)
        top_sub_idx = np.argpartition(candidate_scores, -effective_k)[-effective_k:]
        sorted_sub_idx = top_sub_idx[np.argsort(-candidate_scores[top_sub_idx])]
        final_indices = candidate_indices[sorted_sub_idx[:top_n]]
    elif sort_by == "rating":
        # Sort by rating, break ties by similarity
        sub_df = df.iloc[candidate_indices].copy()
        sub_df["score"] = candidate_scores
        sorted_sub = sub_df.sort_values(by=["rating_num", "score"], ascending=[False, False])
        final_indices = sorted_sub.index.to_numpy()[:top_n]
    elif sort_by in ("price_asc", "price_desc"):
        sub_df = df.iloc[candidate_indices].copy()
        sub_df["score"] = candidate_scores
        sub_df["num_price"] = sub_df["discount_price"].apply(parse_price_to_numeric)
        ascending = (sort_by == "price_asc")
        sorted_sub = sub_df.sort_values(by=["num_price", "score"], ascending=[ascending, False])
        final_indices = sorted_sub.index.to_numpy()[:top_n]
    else:
        effective_k = min(top_n, total_matches)
        top_sub_idx = np.argpartition(candidate_scores, -effective_k)[-effective_k:]
        sorted_sub_idx = top_sub_idx[np.argsort(-candidate_scores[top_sub_idx])]
        final_indices = candidate_indices[sorted_sub_idx]

    # 5. Format results into ProductItem schemas
    results: List[ProductItem] = []
    for idx in final_indices:
        row = df.iloc[idx]
        sim_score = round(float(similarity_scores[idx]), 4)
        
        # Ensure ratings string formatting
        raw_rating = row.get("ratings", "N/A")
        rating_str = str(raw_rating) if pd.notnull(raw_rating) and str(raw_rating).lower() != "nan" else "N/A"
        
        # Price formatting
        discount_price = str(row.get("discount_price", "N/A"))
        if pd.isnull(row.get("discount_price")) or discount_price.lower() == "nan":
            discount_price = "₹" + str(row.get("actual_price", "999"))
            
        actual_price = str(row.get("actual_price", "N/A"))
        if pd.isnull(row.get("actual_price")) or actual_price.lower() == "nan":
            actual_price = discount_price

        # Image fallback
        img_url = row.get("image")
        if pd.isnull(img_url) or not str(img_url).startswith("http"):
            img_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60"

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
                discount_price=discount_price,
                actual_price=actual_price,
                similarity_score=sim_score,
                model_route=model_route_label,
            )
        )

    return results, total_matches
