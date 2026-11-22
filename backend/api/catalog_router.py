from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from backend.api.deps import get_catalog_repo
from backend.models.product import CatalogRepository, Product

router = APIRouter(tags=["catalog"])

@router.get("/products", response_model=List[Product])
def list_products(
    category: Optional[str] = Query(None, description="Filter by garment category (shirt, top, dress)"),
    repo: CatalogRepository = Depends(get_catalog_repo)
):
    """Retrieve catalog products with optional category filtering."""
    return repo.list_products(category=category)

@router.get("/products/{product_id}", response_model=Product)
def get_product(
    product_id: str,
    repo: CatalogRepository = Depends(get_catalog_repo)
):
    """Retrieve a single product by ID."""
    product = repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")
    return product

@router.get("/products/{product_id}/image")
def get_product_image(
    product_id: str,
    repo: CatalogRepository = Depends(get_catalog_repo)
):
    """Serve the product garment image asset."""
    img_path = repo.get_product_image_path(product_id)
    if not img_path or not img_path.exists():
        raise HTTPException(status_code=404, detail="Product image not found.")
    return FileResponse(str(img_path), media_type="image/png")
