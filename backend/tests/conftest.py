import io
import pytest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services.tryon_service import set_custom_engine, reset_custom_engine, RESULTS_DIR

@pytest.fixture(autouse=True)
def setup_and_teardown_mock_engine():
    """Default mock engine for tests that mimics successful try-on without GPU."""
    def mock_loader():
        pass  # successfully loads

    def mock_runner(person_path, garment_path, cloth_type="upper", **kwargs):
        # Generate a test output image
        out_file = RESULTS_DIR / f"test_result_{cloth_type}.png"
        im = Image.new("RGB", (768, 1024), color=(120, 150, 180))
        im.save(out_file)
        return str(out_file)

    set_custom_engine(loader=mock_loader, runner=mock_runner)
    yield
    reset_custom_engine()

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def sample_user_image_bytes():
    buf = io.BytesIO()
    im = Image.new("RGB", (512, 640), color=(180, 160, 140))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(im)
    draw.ellipse([150, 100, 360, 320], fill=(220, 190, 170), outline=(60, 40, 30), width=4)
    draw.rectangle([100, 320, 412, 600], fill=(80, 100, 140), outline=(40, 50, 70), width=4)
    im.save(buf, format="PNG")
    return buf.getvalue()
