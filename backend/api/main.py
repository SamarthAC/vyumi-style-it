import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.catalog_router import router as catalog_router
from backend.api.tryon_router import router as tryon_router
from backend.api.deps import get_catalog_repo, get_job_manager
from backend.services.tryon_service import load_model, is_engine_ready, get_engine_error, TryOnError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vyumi.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager:
    - Call load_model() once at startup.
    - Explicitly handle initialization failure without falsely reporting readiness.
    - Start background job queue worker.
    """
    logger.info("Initializing Vyumi backend and Try-on engine...")

    # Initialize Try-On Engine
    try:
        load_model()
        logger.info("CatVTON Try-on engine loaded successfully.")
    except TryOnError as e:
        logger.warning(f"Try-on engine initialization failed ({e.code}): {e.message}. Backend will run with engine unavailable.")
    except Exception as e:
        logger.error(f"Unexpected try-on engine initialization failure: {e}. Backend will run with engine unavailable.")

    # Start background job worker
    job_mgr = get_job_manager()
    job_mgr.start_worker()

    yield

    # Shutdown
    logger.info("Shutting down Vyumi backend...")
    job_mgr.stop_worker()

app = FastAPI(
    title="Vyumi Virtual Try-On API",
    description="Backend API for 'Style It Your Way' virtual try-on and product catalog.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(catalog_router)
app.include_router(tryon_router)

@app.get("/health", tags=["system"])
def health_check():
    """Health check endpoint exposing system readiness and catalog status."""
    catalog = get_catalog_repo()
    engine_error = get_engine_error()
    return {
        "status": "healthy",
        "engine_ready": is_engine_ready(),
        "engine_error": {
            "code": engine_error.code,
            "message": engine_error.message
        } if engine_error else None,
        "product_count": catalog.count()
    }
