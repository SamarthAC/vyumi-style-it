import time
from backend.models.product import get_cloth_type_for_category
from backend.services.tryon_service import set_custom_engine, RESULTS_DIR
from PIL import Image

def test_cloth_type_category_mapping_helper():
    assert get_cloth_type_for_category("shirt") == "upper"
    assert get_cloth_type_for_category("SHIRTS") == "upper"
    assert get_cloth_type_for_category("top") == "upper"
    assert get_cloth_type_for_category("t-shirt") == "upper"
    assert get_cloth_type_for_category("dress") == "overall"
    assert get_cloth_type_for_category("gown") == "overall"
    assert get_cloth_type_for_category("shoes") is None
    assert get_cloth_type_for_category("pants") is None

def test_shirt_routes_to_upper(client, sample_user_image_bytes):
    passed_cloth_types = []
    def spy_runner(person_path, garment_path, cloth_type="upper", **kwargs):
        passed_cloth_types.append(cloth_type)
        out = RESULTS_DIR / "shirt_out.png"
        Image.new("RGB", (768, 1024)).save(out)
        return str(out)

    set_custom_engine(loader=lambda: None, runner=spy_runner)

    # 1. Upload photo
    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    # 2. Generate with shirt
    gen = client.post("/style-it/generate", json={"user_image_id": user_img_id, "product_id": "prod_shirt_classic_white"})
    assert gen.status_code == 202
    job_id = gen.json()["job_id"]

    # Allow worker to process
    for _ in range(20):
        time.sleep(0.05)
        status = client.get(f"/style-it/jobs/{job_id}").json()
        if status["status"] in ("completed", "failed"):
            break

    assert status["status"] == "completed"
    assert passed_cloth_types == ["upper"]

def test_top_routes_to_upper(client, sample_user_image_bytes):
    passed_cloth_types = []
    def spy_runner(person_path, garment_path, cloth_type="upper", **kwargs):
        passed_cloth_types.append(cloth_type)
        out = RESULTS_DIR / "top_out.png"
        Image.new("RGB", (768, 1024)).save(out)
        return str(out)

    set_custom_engine(loader=lambda: None, runner=spy_runner)

    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    gen = client.post("/style-it/generate", json={"user_image_id": user_img_id, "product_id": "prod_top_floral_summer"})
    assert gen.status_code == 202
    job_id = gen.json()["job_id"]

    for _ in range(20):
        time.sleep(0.05)
        status = client.get(f"/style-it/jobs/{job_id}").json()
        if status["status"] in ("completed", "failed"):
            break

    assert status["status"] == "completed"
    assert passed_cloth_types == ["upper"]

def test_dress_routes_to_overall(client, sample_user_image_bytes):
    passed_cloth_types = []
    def spy_runner(person_path, garment_path, cloth_type="upper", **kwargs):
        passed_cloth_types.append(cloth_type)
        out = RESULTS_DIR / "dress_out.png"
        Image.new("RGB", (768, 1024)).save(out)
        return str(out)

    set_custom_engine(loader=lambda: None, runner=spy_runner)

    up = client.post("/style-it/upload", files={"file": ("u.png", sample_user_image_bytes, "image/png")})
    user_img_id = up.json()["user_image_id"]

    gen = client.post("/style-it/generate", json={"user_image_id": user_img_id, "product_id": "prod_dress_evening_velvet"})
    assert gen.status_code == 202
    job_id = gen.json()["job_id"]

    for _ in range(20):
        time.sleep(0.05)
        status = client.get(f"/style-it/jobs/{job_id}").json()
        if status["status"] in ("completed", "failed"):
            break

    assert status["status"] == "completed"
    assert passed_cloth_types == ["overall"]
