# VYUMI: Style It Your Way (Feature 1)

> Internal prototype. Try-on models used here are CC BY-NC-SA 4.0 (non-commercial).

## What it does

Upload a user portrait photo, select an apparel product from the curated catalog (shirts, tops, dresses), and generate a realistic virtual try-on image.

## Inputs

- **User Image**: Uploaded via `POST /style-it/upload` (`multipart/form-data`, JPEG/PNG/WebP, max 10 MB). Returns `user_image_id`.
- **Product ID**: Curated catalog apparel item (`prod_shirt_classic_white`, `prod_top_floral_summer`, `prod_dress_evening_velvet`).

## Outputs

- **Try-On Generation Job**: `POST /style-it/generate` returns `{ "job_id": "<uuid>", "status": "pending" }`.
- **Job Status & Result**: Polled via `GET /style-it/jobs/{id}`:
  - Completed: `{ "status": "completed", "result_image_url": "/style-it/results/<id>.png" }`
  - Failed: `{ "status": "failed", "error_code": "<code>", "message": "<message>" }`
- **Result Image Asset**: Rendered $768 \times 1024$ PNG served at `GET /style-it/results/{filename}`.

## Local setup

### 1. Conda Environment (`catvton`)

The virtual try-on engine requires Python 3.9 with CUDA-enabled PyTorch:

```bash
# Create and activate conda environment
conda create -n catvton python=3.9 -y
conda activate catvton

# Install PyTorch with CUDA 12.1
conda install -y -c pytorch -c nvidia pytorch==2.4.0 torchvision torchaudio pytorch-cuda=12.1
conda install -y matplotlib

# Install CatVTON requirements and backend dependencies
pip install diffusers==0.30.0 pydantic==2.10.6 accelerate
pip install -r backend/requirements.txt
```

### 2. CatVTON Model Repository

Clone or place the CatVTON source into `third_party/CatVTON` (gitignored).

## Model(s) used

- **CatVTON**: Inpainting-based virtual try-on network combining `CatVTONPipeline` (`booksforcharlie/stable-diffusion-inpainting` base + `zhengchong/CatVTON` weights) with `AutoMasker` (`DensePose` and `SCHP`).
- **Precision**: `bf16` (fallback to `fp16` if VRAM constrained).
- **Target Resolution**: $768 \times 1024$.

## Data files

- `backend/data/catalog.db`: SQLite database caching curated products.
- `backend/data/products/catalog.json`: Seed catalog with product metadata and cloth type routing.
- `backend/data/products/`: Garment asset images.
- `backend/data/uploads/`: Gitignored local user uploads directory.
- `backend/data/results/`: Gitignored local try-on results directory.

## Run command

```bash
# Set GPU device (if multi-GPU system)
set CUDA_VISIBLE_DEVICES=0

# Start backend server
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- System Health: `http://localhost:8000/health`

## Test command

Run the automated backend test suite (runs with mock engine calls without downloading model weights or requiring GPU):

```bash
pytest backend/tests -v
```

Run manual try-on GPU benchmark (requires CUDA GPU and CatVTON weights):

```bash
python backend/scripts/test_tryon.py path/to/person.jpg path/to/garment.jpg upper
```

## Golden examples

- Shirt / Top: Maps category `shirt` or `top` to `cloth_type="upper"`.
- Dress: Maps category `dress` to `cloth_type="overall"`.
- Reference sample outputs are preserved in `docs/sample/*.png`.

## Known limitations

1. **Hardware Requirements**: Full CatVTON inference requires an NVIDIA GPU with at least 8 GB VRAM (e.g., RTX 4060 or better). Low-memory GPUs (such as 2 GB MX350) will raise `OUT_OF_MEMORY` or `NO_GPU`.
2. **Prototype Scope**: Restricted to upper garments (shirts, tops) and overall garments (dresses). Bottoms/shoes/accessories are deliberately unsupported in this prototype.
3. **Serialized Queue**: Inference is strictly serialized to 1 active GPU job at a time to prevent VRAM spikes.

## License notes

- CatVTON model checkpoints and architectures are licensed under **CC BY-NC-SA 4.0 (Creative Commons Non-Commercial ShareAlike)**.
- Usage is restricted to internal research, evaluation, and prototype demonstrations only. Commercial distribution or hosted monetization is prohibited under this license.

## Troubleshooting

- **`503 Service Unavailable: Try-on engine unavailable: No GPU found`**:
  The backend detected no compatible CUDA device. The API remains operational for catalog browsing and upload validation, but generation requests are rejected safely.
- **`TryOnError: OUT_OF_MEMORY`**:
  GPU VRAM ran out during diffusion steps. Try switching `TRYON_PRECISION=fp16` or reducing `DEFAULT_STEPS=30`.
- **`400 Bad Request: Unsupported product category`**:
  Ensure the product category is one of `shirt`, `top`, or `dress`.
