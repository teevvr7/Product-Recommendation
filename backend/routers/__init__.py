"""
API Routers package for recommendations, multi-model comparisons, product browsing, and system health.
"""
from .recommend import router as recommend_router
from .compare import router as compare_router
from .products import router as products_router
from .system import router as system_router

__all__ = ["recommend_router", "compare_router", "products_router", "system_router"]
