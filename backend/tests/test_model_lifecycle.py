import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services.tryon_service import (
    load_model,
    set_custom_engine,
    reset_custom_engine,
    is_engine_ready,
    get_engine_error,
    TryOnError
)

def test_model_initialization_success():
    call_count = 0
    def mock_loader():
        nonlocal call_count
        call_count += 1

    set_custom_engine(loader=mock_loader, mark_ready=False)
    load_model()
    assert is_engine_ready() is True
    assert get_engine_error() is None
    assert call_count == 1

    # Calling again should be idempotent
    load_model()
    assert call_count == 1
    assert is_engine_ready() is True

def test_model_initialization_failure_rejects_generation(sample_user_image_bytes):
    def failing_loader():
        raise TryOnError("NO_GPU", "No GPU found for the try-on engine.")

    set_custom_engine(loader=failing_loader, mark_ready=False)

    with TestClient(app) as test_client:
        # Engine should NOT be marked ready
        assert is_engine_ready() is False
        err = get_engine_error()
        assert err is not None
        assert err.code == "NO_GPU"

        # Upload an image
        up_res = test_client.post(
            "/style-it/upload",
            files={"file": ("photo.png", sample_user_image_bytes, "image/png")}
        )
        assert up_res.status_code == 200
        user_img_id = up_res.json()["user_image_id"]

        # Attempt generation - must be rejected with 503 and not falsely report readiness
        gen_res = test_client.post(
            "/style-it/generate",
            json={"user_image_id": user_img_id, "product_id": "prod_shirt_classic_white"}
        )
        assert gen_res.status_code == 503
        assert "unavailable" in gen_res.json()["detail"].lower()
