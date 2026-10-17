# Vyumi Virtual Try-On API Specification

## 1. Product Catalog

### `GET /products`
List all apparel products. Optional filter by category: `?category=shirt`, `?category=top`, `?category=dress`.

### `GET /products/{id}`
Retrieve product details by ID. Returns `404 Not Found` if missing.

### `GET /products/{id}/image`
Retrieve product garment asset image (`image/png`).

---

## 2. Virtual Try-On ("Style It Your Way")

### `POST /style-it/upload`
Upload user portrait photo.
- **Validation**:
  - File formats: JPEG, PNG, WebP only.
  - File size: Capped at 10 MB.
  - Resolution: Minimum 512 pixels along the short side.
  - Brightness: Balanced luminance (average brightness between 30 and 240).
  - Sharpness: Rejects blurry or featureless inputs (edge variance $\ge 5.0$).
  - Integrity: Decoded and verified via PIL.
  - *Note:* Multi-person count and pose/torso checks belong to the validation workstream (`feature/validation`).
- **Response**:
```json
{
  "user_image_id": "9f3f4c78a0b14643b4f6e1f0e4235882"
}
```

### `POST /style-it/generate`
Submit a virtual try-on job.
- **Request**:
```json
{
  "user_image_id": "9f3f4c78a0b14643b4f6e1f0e4235882",
  "product_id": "prod_shirt_classic_white"
}
```
- **Response** (`202 Accepted`):
```json
{
  "job_id": "e6a18d1a1b5247cca56f4d1e2e3f5a11",
  "status": "pending"
}
```
- **Error Responses**:
  - `503 Service Unavailable`: If model initialization failed at startup.
  - `400 Bad Request`: If user image or product ID is invalid or category unsupported.

### `GET /style-it/jobs/{id}`
Poll job execution status.

#### When Pending / Processing:
```json
{
  "status": "pending"
}
```

#### When Completed:
```json
{
  "status": "completed",
  "result_image_url": "/style-it/results/b94e019313db433db99684b025cb7e39.png"
}
```

#### When Failed (`TryOnError` contract):
```json
{
  "status": "failed",
  "error_code": "OUT_OF_MEMORY",
  "message": "We could not generate the result. Try another image or product."
}
```

#### When Unknown:
`404 Not Found` with `{ "detail": "Job not found" }`.

---

## 3. Results

### `GET /style-it/results/{filename}`
Download rendered PNG try-on output. Guards against directory traversal attacks.
