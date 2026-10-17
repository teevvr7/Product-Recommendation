import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.services.model_loader import registry
from backend.routers import (
    recommend_router,
    compare_router,
    products_router,
    system_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("acme_recommender")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager:
    Loads pre-trained Word2Vec, FastText, and TF-IDF artifacts into memory at startup.
    """
    logger.info("Initializing Acme Retail Product Recommendation Engine...")
    registry.load_artifacts()
    logger.info("Ready to serve semantic similarity recommendations!")
    yield
    logger.info("Shutting down Acme Retail recommendation service.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local development and testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(recommend_router, prefix="/api")
app.include_router(compare_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(system_router, prefix="/api")

# Ensure frontend static directory exists
settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
async def serve_homepage():
    """Serves the main e-commerce interface."""
    index_path = settings.FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Acme Retail Semantic Recommendation API is running. Visit /docs for Swagger UI."}
