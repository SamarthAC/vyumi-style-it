import io
import time
from PIL import Image, ImageDraw, ImageFilter
from backend.services.storage_service import StorageService

def test_valid_image_upload(client, sample_user_image_bytes):
    response = client.post(
        "/style-it/upload",
        files={"file": ("me.png", sample_user_image_bytes, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_image_id" in data
    assert len(data["user_image_id"]) > 0

def test_empty_file_upload_rejected(client):
    response = client.post(
        "/style-it/upload",
        files={"file": ("empty.png", b"", "image/png")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_corrupted_image_upload_rejected(client):
    response = client.post(
        "/style-it/upload",
        files={"file": ("corrupt.png", b"NOT_A_REAL_IMAGE_DATA", "image/png")}
    )
    assert response.status_code == 400
    assert "not a valid" in response.json()["detail"].lower()

def test_unsupported_mime_type_rejected(client):
    response = client.post(
        "/style-it/upload",
        files={"file": ("doc.pdf", b"%PDF-1.4...", "application/pdf")}
    )
    assert response.status_code == 400
    assert "unsupported content type" in response.json()["detail"].lower()

def test_oversized_file_rejected(client):
    oversized = b"0" * (11 * 1024 * 1024)
    response = client.post(
        "/style-it/upload",
        files={"file": ("large.png", oversized, "image/png")}
    )
    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"].lower()

def test_resolution_under_512px_short_side_rejected(client):
    # Image 400x600 has short side 400 < 512
    im = Image.new("RGB", (400, 600), color=(180, 160, 140))
    draw = ImageDraw.Draw(im)
    draw.rectangle([50, 50, 350, 550], fill=(50, 80, 120))
    buf = io.BytesIO()
    im.save(buf, format="PNG")

    response = client.post(
        "/style-it/upload",
        files={"file": ("small.png", buf.getvalue(), "image/png")}
    )
    assert response.status_code == 400
    assert "short side must be at least 512 pixels" in response.json()["detail"].lower()

def test_too_dark_image_rejected(client):
    # Image with mean brightness ~ 10 < 30
    im = Image.new("RGB", (600, 800), color=(10, 10, 10))
    draw = ImageDraw.Draw(im)
    draw.rectangle([100, 100, 500, 700], fill=(20, 20, 20))
    buf = io.BytesIO()
    im.save(buf, format="PNG")

    response = client.post(
        "/style-it/upload",
        files={"file": ("dark.png", buf.getvalue(), "image/png")}
    )
    assert response.status_code == 400
    assert "too dark" in response.json()["detail"].lower()

def test_overexposed_image_rejected(client):
    # Image with mean brightness ~ 250 > 240
    im = Image.new("RGB", (600, 800), color=(252, 252, 252))
    draw = ImageDraw.Draw(im)
    draw.rectangle([100, 100, 500, 700], fill=(245, 245, 245))
    buf = io.BytesIO()
    im.save(buf, format="PNG")

    response = client.post(
        "/style-it/upload",
        files={"file": ("bright.png", buf.getvalue(), "image/png")}
    )
    assert response.status_code == 400
    assert "overexposed" in response.json()["detail"].lower()

def test_blurry_featureless_image_rejected(client):
    # Completely flat image with no edge contrast
    im = Image.new("RGB", (600, 800), color=(128, 128, 128))
    buf = io.BytesIO()
    im.save(buf, format="PNG")

    response = client.post(
        "/style-it/upload",
        files={"file": ("flat.png", buf.getvalue(), "image/png")}
    )
    assert response.status_code == 400
    assert "blurry or featureless" in response.json()["detail"].lower()

def test_storage_cleanup_expired_files(tmp_path):
    uploads = tmp_path / "uploads"
    results = tmp_path / "results"
    storage = StorageService(uploads_dir=uploads, results_dir=results)

    # Create dummy active file and old expired file
    active_file = uploads / "active.png"
    active_file.write_text("active")

    old_file = uploads / "old.png"
    old_file.write_text("old")
    # Set old timestamp (2 days ago)
    past_time = time.time() - (2 * 86400)
    import os
    os.utime(old_file, (past_time, past_time))

    keep_file = uploads / ".gitkeep"
    keep_file.write_text("")
    os.utime(keep_file, (past_time, past_time))

    # Run cleanup for files older than 1 day
    deleted = storage.cleanup_expired_files(max_age_seconds=86400)
    assert deleted == 1
    assert active_file.exists()
    assert keep_file.exists()
    assert not old_file.exists()
