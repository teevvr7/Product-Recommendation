from typing import List, Dict, Any, Optional
import pandas as pd
from backend.services.model_loader import registry
from backend.schemas.product import ProductItem, ProductDetail, CatalogBrowseResponse

def get_product_by_id(catalog_id: int) -> Optional[ProductDetail]:
    """Retrieves full product detail by catalog index."""
    df = registry.catalog_df
    if df is None or catalog_id < 0 or catalog_id >= len(df):
        return None

    row = df.iloc[catalog_id]
    
    # Extract first 5 dimensions of vector as preview
    w2v_vec = row.get("w2v_vector")
    preview = []
    if w2v_vec is not None and len(w2v_vec) > 0:
        preview = [round(float(v), 4) for v in w2v_vec[:5]]

    raw_rating = row.get("ratings", "N/A")
    rating_str = str(raw_rating) if pd.notnull(raw_rating) and str(raw_rating).lower() != "nan" else "N/A"

    img_url = row.get("image")
    if pd.isnull(img_url) or not str(img_url).startswith("http"):
        img_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60"

    return ProductDetail(
        catalog_id=catalog_id,
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
        similarity_score=1.0,
        model_route="Catalog Item",
        combined_raw_text=str(row.get("combined_raw_text", "")),
        cleaned_text=str(row.get("cleaned_text", "")),
        vector_preview=preview,
    )

def browse_catalog(
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    keyword: Optional[str] = None
) -> CatalogBrowseResponse:
    """Browse catalog products with pagination, category filter, and keyword search."""
    df = registry.catalog_df
    if df is None:
        return CatalogBrowseResponse(total=0, page=page, page_size=page_size, total_pages=0, items=[])

    filtered = df
    if category and category.lower() != "all":
        filtered = filtered[filtered["main_category"].str.lower() == category.lower()]

    if keyword and keyword.strip():
        kw = keyword.strip().lower()
        filtered = filtered[filtered["name"].str.lower().str.contains(kw, na=False)]

    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total)
    sub_df = filtered.iloc[start_idx:end_idx]

    items: List[ProductItem] = []
    for idx, row in sub_df.iterrows():
        c_id = int(row.get("catalog_id", idx))
        raw_rating = row.get("ratings", "N/A")
        rating_str = str(raw_rating) if pd.notnull(raw_rating) and str(raw_rating).lower() != "nan" else "N/A"
        img_url = row.get("image")
        if pd.isnull(img_url) or not str(img_url).startswith("http"):
            img_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60"

        items.append(
            ProductItem(
                catalog_id=c_id,
                name=str(row.get("name", "Unknown")),
                main_category=str(row.get("main_category", "General")),
                sub_category=str(row.get("sub_category", "General")),
                image=str(img_url),
                link=str(row.get("link", "#")),
                ratings=rating_str,
                rating_num=float(row.get("rating_num", 0.0)),
                no_of_ratings=str(row.get("no_of_ratings", "0")),
                discount_price=str(row.get("discount_price", "N/A")),
                actual_price=str(row.get("actual_price", "N/A")),
                similarity_score=None,
                model_route=None,
            )
        )

    return CatalogBrowseResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )

def get_categories_data() -> Dict[str, Any]:
    """Returns list of categories with product counts."""
    return {
        "categories": registry.categories,
        "counts": registry.category_counts,
        "total_catalog": registry.total_products,
    }
