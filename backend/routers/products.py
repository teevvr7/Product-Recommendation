from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from backend.schemas.product import ProductDetail, CatalogBrowseResponse
from backend.services.catalog_service import (
    get_product_by_id,
    browse_catalog,
    get_categories_data,
)

router = APIRouter(prefix="/products", tags=["Product Catalog"])

@router.get("", response_model=CatalogBrowseResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None)
):
    """Browse catalog with pagination and optional filters."""
    return browse_catalog(page=page, page_size=page_size, category=category, keyword=keyword)

@router.get("/categories/all", response_model=Dict[str, Any])
def get_categories():
    """Retrieve all available main categories and product counts."""
    return get_categories_data()

@router.get("/{catalog_id}", response_model=ProductDetail)
def get_product(catalog_id: int):
    """Retrieve full product profile and vector preview by catalog ID."""
    prod = get_product_by_id(catalog_id)
    if prod is None:
        raise HTTPException(status_code=404, detail=f"Product with catalog ID {catalog_id} was not found.")
    return prod
