import time
from backend.services.tryon_service import set_custom_engine, RESULTS_DIR
from PIL import Image

def test_queue_serializes_multiple_jobs(client, sample_user_image_bytes):
    concurrency_check = []
    active_jobs = 0

    def slow_runner(person_path, garment_path, cloth_type="upper", **kwargs):
        nonlocal active_jobs
        active_jobs += 1
        concurrency_check.append(active_jobs)
        time.sleep(0.1)  # simulate model work
        active_jobs -= 1
        out = RESULTS_DIR / f"seq_{cloth_type}.png"
        Image.new("RGB", (768, 1024)).save(out)
        return str(out)

    set_custom_engine(loader=lambda: None, runner=slow_runner)

    # Upload user image
    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    # Submit 3 jobs in rapid succession
    job_ids = []
    for pid in ["prod_shirt_classic_white", "prod_top_floral_summer", "prod_dress_evening_velvet"]:
        res = client.post("/style-it/generate", json={"user_image_id": user_img_id, "product_id": pid})
        assert res.status_code == 202
        job_ids.append(res.json()["job_id"])

    # Wait for all jobs to complete
    for job_id in job_ids:
        for _ in range(50):
            time.sleep(0.05)
            status = client.get(f"/style-it/jobs/{job_id}").json()
            if status["status"] == "completed":
                break
        assert status["status"] == "completed"

    # Verify that at no point were multiple jobs running concurrently in the runner
    assert all(c == 1 for c in concurrency_check), f"Concurrency violated: {concurrency_check}"
    assert len(concurrency_check) == 3

def test_result_image_retrieval_and_path_traversal_protection(client, sample_user_image_bytes):
    # 1. Successful job
    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    gen = client.post("/style-it/generate", json={"user_image_id": user_img_id, "product_id": "prod_shirt_classic_white"})
    job_id = gen.json()["job_id"]

    for _ in range(20):
        time.sleep(0.05)
        status = client.get(f"/style-it/jobs/{job_id}").json()
        if status["status"] == "completed":
            break

    result_url = status["result_image_url"]
    filename = result_url.split("/")[-1]

    # Retrieve valid result
    res = client.get(f"/style-it/results/{filename}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 0

    # Path traversal attack
    traversal_res = client.get("/style-it/results/../../../../etc/passwd")
    assert traversal_res.status_code in (404, 400)

    traversal_res2 = client.get("/style-it/results/..%2F..%2F..%2Fwindows%2Fwin.ini")
    assert traversal_res2.status_code in (404, 400)
