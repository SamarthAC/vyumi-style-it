import time
from backend.services.tryon_service import set_custom_engine, TryOnError

def test_successful_job_contract(client, sample_user_image_bytes):
    # Upload user image
    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    # Generate job
    gen = client.post(
        "/style-it/generate",
        json={"user_image_id": user_img_id, "product_id": "prod_shirt_classic_white"}
    )
    assert gen.status_code == 202
    data = gen.json()
    assert "job_id" in data
    assert data["status"] == "pending"

    job_id = data["job_id"]

    # Poll status
    for _ in range(20):
        time.sleep(0.05)
        status_res = client.get(f"/style-it/jobs/{job_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        if status_data["status"] == "completed":
            break

    assert status_data["status"] == "completed"
    assert "result_image_url" in status_data
    assert status_data["result_image_url"].startswith("/style-it/results/")

def test_tryon_error_contract_propagation(client, sample_user_image_bytes):
    """Verify exact TryOnError failure contract: { 'status': 'failed', 'error_code': '...', 'message': '...' }"""
    def failing_runner(*args, **kwargs):
        raise TryOnError("OUT_OF_MEMORY", "We could not generate the result. Try another image or product.")

    set_custom_engine(loader=lambda: None, runner=failing_runner)

    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    gen = client.post(
        "/style-it/generate",
        json={"user_image_id": user_img_id, "product_id": "prod_shirt_classic_white"}
    )
    assert gen.status_code == 202
    job_id = gen.json()["job_id"]

    # Poll until failed
    for _ in range(20):
        time.sleep(0.05)
        status_res = client.get(f"/style-it/jobs/{job_id}")
        status_data = status_res.json()
        if status_data["status"] == "failed":
            break

    assert status_data == {
        "status": "failed",
        "error_code": "OUT_OF_MEMORY",
        "message": "We could not generate the result. Try another image or product."
    }

def test_unexpected_exception_fails_cleanly_without_leak(client, sample_user_image_bytes):
    """Unexpected exception should produce failed status with friendly message and no stack trace."""
    def crash_runner(*args, **kwargs):
        raise RuntimeError("Fatal CUDA crash at memory address 0xdeadbeef /home/secret/catvton")

    set_custom_engine(loader=lambda: None, runner=crash_runner)

    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    gen = client.post(
        "/style-it/generate",
        json={"user_image_id": user_img_id, "product_id": "prod_shirt_classic_white"}
    )
    job_id = gen.json()["job_id"]

    for _ in range(20):
        time.sleep(0.05)
        status_res = client.get(f"/style-it/jobs/{job_id}")
        status_data = status_res.json()
        if status_data["status"] == "failed":
            break

    assert status_data["status"] == "failed"
    assert status_data["error_code"] == "INTERNAL_ERROR"
    # Ensure sensitive system paths or stack traces are not leaked
    assert "0xdeadbeef" not in status_data["message"]
    assert "secret" not in status_data["message"]

def test_unknown_job_id_returns_404(client):
    response = client.get("/style-it/jobs/unknown-job-id-99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"

def test_generate_with_missing_user_image(client):
    response = client.post(
        "/style-it/generate",
        json={"user_image_id": "non_existent_img_id", "product_id": "prod_shirt_classic_white"}
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()

def test_generate_with_invalid_product_id(client, sample_user_image_bytes):
    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    response = client.post(
        "/style-it/generate",
        json={"user_image_id": user_img_id, "product_id": "invalid_prod_9999"}
    )
    assert response.status_code == 400
    assert "not found in catalog" in response.json()["detail"].lower()
