import json
import sqlite3
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_DB_PATH = REPO_ROOT / "backend" / "data" / "catalog.db"
SEED_DATA_PATH = REPO_ROOT / "backend" / "data" / "products" / "catalog.json"
PRODUCT_IMAGES_DIR = REPO_ROOT / "backend" / "data" / "products"

class Product(BaseModel):
    id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product display name")
    category: str = Field(..., description="Garment category: shirt, top, dress")
    cloth_type: str = Field(..., description="Target engine cloth type: upper or overall")
    description: str = Field(..., description="Product description")
    image_filename: str = Field(..., description="Product image filename")
    image_url: Optional[str] = Field(None, description="URL endpoint to retrieve product image")

def get_cloth_type_for_category(category: str) -> Optional[str]:
    """Map garment category to try-on engine cloth_type.
    - shirts and tops -> 'upper'
    - dresses -> 'overall'
    - others -> None (unsupported)
    """
    cat = category.strip().lower()
    if cat in ("shirt", "shirts", "top", "tops", "tshirt", "t-shirt"):
        return "upper"
    elif cat in ("dress", "dresses", "gown", "frock"):
        return "overall"
    return None

class CatalogRepository:
    def __init__(self, db_path: Path = CATALOG_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    cloth_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    image_filename TEXT NOT NULL
                )
            """)
            conn.commit()

        # Seed catalog if empty
        if self.count() == 0:
            self.seed_defaults()

    def count(self) -> int:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM products")
            return cur.fetchone()[0]

    def seed_defaults(self):
        items = []
        if SEED_DATA_PATH.exists():
            try:
                with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
                    items = json.load(f)
            except Exception:
                items = []

        if not items:
            items = [
                {
                    "id": "prod_shirt_classic_white",
                    "name": "Classic White Linen Shirt",
                    "category": "shirt",
                    "cloth_type": "upper",
                    "description": "Breathable pure linen button-down white shirt.",
                    "image_filename": "shirt_classic_white.png"
                },
                {
                    "id": "prod_top_floral_summer",
                    "name": "Floral Summer Sleeveless Top",
                    "category": "top",
                    "cloth_type": "upper",
                    "description": "Lightweight pastel floral summer top.",
                    "image_filename": "top_floral_summer.png"
                },
                {
                    "id": "prod_dress_evening_velvet",
                    "name": "Emerald Evening Midi Dress",
                    "category": "dress",
                    "cloth_type": "overall",
                    "description": "Tailored emerald green evening dress with elegant silhouette.",
                    "image_filename": "dress_evening_velvet.png"
                }
            ]

        with self._get_connection() as conn:
            for item in items:
                cloth_type = item.get("cloth_type") or get_cloth_type_for_category(item["category"]) or "upper"
                conn.execute("""
                    INSERT OR REPLACE INTO products (id, name, category, cloth_type, description, image_filename)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (item["id"], item["name"], item["category"], cloth_type, item["description"], item["image_filename"]))
            conn.commit()

    def list_products(self, category: Optional[str] = None) -> List[Product]:
        query = "SELECT * FROM products"
        params = []
        if category:
            query += " WHERE LOWER(category) = LOWER(?)"
            params.append(category.strip())

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                Product(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    cloth_type=row["cloth_type"],
                    description=row["description"],
                    image_filename=row["image_filename"],
                    image_url=f"/products/{row['id']}/image"
                )
                for row in rows
            ]

    def get_product(self, product_id: str) -> Optional[Product]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if not row:
                return None
            return Product(
                id=row["id"],
                name=row["name"],
                category=row["category"],
                cloth_type=row["cloth_type"],
                description=row["description"],
                image_filename=row["image_filename"],
                image_url=f"/products/{row['id']}/image"
            )

    def get_product_image_path(self, product_id: str) -> Optional[Path]:
        prod = self.get_product(product_id)
        if not prod:
            return None
        path = PRODUCT_IMAGES_DIR / prod.image_filename
        return path
