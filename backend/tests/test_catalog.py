def test_list_all_products(client):
    response = client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) >= 3
    # Check required fields
    for p in products:
        assert "id" in p
        assert "name" in p
        assert "category" in p
        assert "cloth_type" in p
        assert "description" in p
        assert "image_url" in p
        assert p["cloth_type"] in ("upper", "overall")

def test_filter_products_by_category(client):
    response_shirt = client.get("/products?category=shirt")
    assert response_shirt.status_code == 200
    for p in response_shirt.json():
        assert p["category"] == "shirt"
        assert p["cloth_type"] == "upper"

    response_dress = client.get("/products?category=dress")
    assert response_dress.status_code == 200
    for p in response_dress.json():
        assert p["category"] == "dress"
        assert p["cloth_type"] == "overall"

def test_get_product_by_id(client):
    response = client.get("/products/prod_shirt_classic_white")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "prod_shirt_classic_white"
    assert data["category"] == "shirt"
    assert data["cloth_type"] == "upper"

def test_get_nonexistent_product_returns_404(client):
    response = client.get("/products/non_existent_product_12345")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_product_image(client):
    response = client.get("/products/prod_shirt_classic_white/image")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0
