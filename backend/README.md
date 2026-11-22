# Vyumi Backend Architecture & Engine Integration

This module provides the core backend services for the Vyumi "Style It Your Way" virtual try-on application.

## Directory Structure

- `api/`: FastAPI route handlers and dependency injection.
  - `main.py`: Application factory, lifespan initialization, CORS, and health checks.
  - `catalog_router.py`: Product catalog browsing (`GET /products`, `GET /products/{id}`, `GET /products/{id}/image`).
  - `tryon_router.py`: Try-on workflows (`POST /style-it/upload`, `POST /style-it/generate`, `GET /style-it/jobs/{id}`, `GET /style-it/results/{filename}`).
  - `deps.py`: Shared dependencies and service singletons.
- `models/`: Pydantic V2 models and SQLite repository.
  - `product.py`: Product metadata and category-to-cloth-type mapper (`shirt`/`top` -> `upper`, `dress` -> `overall`).
  - `job.py`: Job schemas and polling response contract.
- `services/`: Core business logic.
  - `storage_service.py`: Secure upload validation (format, size, PIL integrity, path traversal protection).
  - `job_worker.py`: In-process serialized job queue and worker thread managing lifecycle and error mapping.
  - `tryon_service.py`: CatVTON wrapper implementing `load_model()`, `run_tryon()`, `TryOnError`, and test hooks.
- `data/`: Local storage.
  - `products/`: Curated seed catalog (`catalog.json`) and garment image assets.
  - `catalog.db`: SQLite database.
  - `uploads/`: Uploaded user images (gitignored).
  - `results/`: Rendered try-on results (gitignored).
- `tests/`: Pytest test suite covering model lifecycle, routing, error contracts, and upload validation.
