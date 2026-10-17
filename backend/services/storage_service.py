import io
import re
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageFilter, ImageStat

REPO_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = REPO_ROOT / "backend" / "data" / "uploads"
RESULTS_DIR = REPO_ROOT / "backend" / "data" / "results"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_SHORT_SIDE_PIXELS = 512

# Brightness limits (0 to 255)
MIN_BRIGHTNESS = 30.0
MAX_BRIGHTNESS = 240.0

# Minimum edge variance for sharpness
MIN_EDGE_VARIANCE = 5.0

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")

class StorageError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class StorageService:
    def __init__(self, uploads_dir: Path = UPLOADS_DIR, results_dir: Path = RESULTS_DIR):
        self.uploads_dir = uploads_dir
        self.results_dir = results_dir
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def validate_id(self, item_id: str) -> bool:
        return bool(item_id and SAFE_ID_REGEX.match(item_id))

    def validate_image_quality(self, image: Image.Image):
        """Validate resolution, brightness, and sharpness of uploaded user photo."""
        # 1. Short-side resolution minimum 512 pixels
        short_side = min(image.width, image.height)
        if short_side < MIN_SHORT_SIDE_PIXELS:
            raise StorageError(
                f"Image resolution too low ({image.width}x{image.height}). Short side must be at least {MIN_SHORT_SIDE_PIXELS} pixels."
            )

        # 2. Brightness check (luminance)
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        mean_brightness = stat.mean[0]
        if mean_brightness < MIN_BRIGHTNESS:
            raise StorageError(
                f"Image is too dark (average brightness {mean_brightness:.1f}/255). Please upload a well-lit photo."
            )
        if mean_brightness > MAX_BRIGHTNESS:
            raise StorageError(
                f"Image is overexposed/too bright (average brightness {mean_brightness:.1f}/255). Please upload a balanced photo."
            )

        # 3. Blur / Sharpness check via edge variance
        w, h = gray.size
        if w > 4 and h > 4:
            edges = gray.filter(ImageFilter.FIND_EDGES).crop((2, 2, w - 2, h - 2))
            edge_var = ImageStat.Stat(edges).var[0]
            if edge_var < MIN_EDGE_VARIANCE:
                raise StorageError(
                    "Image appears too blurry or featureless. Please upload a clear, focused portrait."
                )

    def save_user_image(self, file_bytes: bytes, original_filename: Optional[str] = None, content_type: Optional[str] = None) -> str:
        if not file_bytes:
            raise StorageError("Uploaded file is empty.")

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise StorageError(f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.")

        if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
            raise StorageError(f"Unsupported content type '{content_type}'. Allowed types are JPEG, PNG, and WebP.")

        # Decode image using PIL to confirm validity and format
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image.verify()  # Verify image integrity
            # Reopen after verify() as recommended by PIL docs
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        except Exception:
            raise StorageError("Uploaded file is not a valid or readable image.")

        # Run quality validations: 512px short-side, brightness, sharpness
        self.validate_image_quality(image)

        image_id = uuid.uuid4().hex
        target_path = self.uploads_dir / f"{image_id}.png"
        image.save(target_path, format="PNG")
        return image_id

    def get_user_image_path(self, user_image_id: str) -> Optional[Path]:
        if not self.validate_id(user_image_id):
            return None
        target = (self.uploads_dir / f"{user_image_id}.png").resolve()
        if not str(target).startswith(str(self.uploads_dir.resolve())):
            return None  # Path traversal attempt
        if target.exists() and target.is_file():
            return target
        return None

    def get_result_image_path(self, filename: str) -> Optional[Path]:
        base_name = Path(filename).name
        target = (self.results_dir / base_name).resolve()
        if not str(target).startswith(str(self.results_dir.resolve())):
            return None  # Path traversal attempt
        if target.exists() and target.is_file():
            return target
        return None

    def cleanup_expired_files(self, max_age_seconds: int = 86400) -> int:
        """Safely delete expired uploads and results older than max_age_seconds without touching active files or .gitkeep."""
        now = time.time()
        removed_count = 0
        for target_dir in (self.uploads_dir, self.results_dir):
            if not target_dir.exists():
                continue
            for item in target_dir.iterdir():
                if item.is_file() and item.name != ".gitkeep":
                    try:
                        if now - item.stat().st_mtime > max_age_seconds:
                            item.unlink()
                            removed_count += 1
                    except OSError:
                        pass
        return removed_count
