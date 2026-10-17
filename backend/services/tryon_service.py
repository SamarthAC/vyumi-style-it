"""
Try-on engine for VYUMI "Style It Your Way".
Wraps CatVTON (CC BY-NC-SA 4.0, non-commercial, prototype only).

Usage:
    load_model()                                  # once, at server start
    path = run_tryon("person.jpg", "shirt.jpg")   # returns result image path
"""
import os
import sys
import threading
import uuid
from pathlib import Path

import torch
from PIL import Image

# --- Paths -------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
CATVTON_DIR = REPO_ROOT / "third_party" / "CatVTON"
RESULTS_DIR = REPO_ROOT / "backend" / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# CatVTON uses imports like `from model.pipeline import ...`
sys.path.insert(0, str(CATVTON_DIR))

# --- Settings ----------------------------------------------------------
BASE_MODEL = "booksforcharlie/stable-diffusion-inpainting"
CHECKPOINT_REPO = "zhengchong/CatVTON"
PRECISION = os.environ.get("TRYON_PRECISION", "bf16")  # try "fp16" if OOM
WIDTH, HEIGHT = 768, 1024
DEFAULT_STEPS = 50       # lower (e.g. 30) = faster, slightly less detail
DEFAULT_CFG = 2.5
DEFAULT_SEED = 42

# --- Errors the API can map to friendly messages -----------------------
class TryOnError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

# --- Internal state ----------------------------------------------------
_pipeline = None
_automasker = None
_mask_processor = None
_lock = threading.Lock()          # one job at a time on the GPU
_load_lock = threading.Lock()


def load_model():
    """Load CatVTON once. Safe to call multiple times."""
    global _pipeline, _automasker, _mask_processor
    with _load_lock:
        if _pipeline is not None:
            return
        if not torch.cuda.is_available():
            raise TryOnError("NO_GPU", "No GPU found for the try-on engine.")

        # Imported here so the CatVTON path is already set up
        from diffusers.image_processor import VaeImageProcessor
        from huggingface_hub import snapshot_download
        from model.cloth_masker import AutoMasker
        from model.pipeline import CatVTONPipeline
        from utils import init_weight_dtype

        repo_path = snapshot_download(repo_id=CHECKPOINT_REPO)

        _pipeline = CatVTONPipeline(
            base_ckpt=BASE_MODEL,
            attn_ckpt=repo_path,
            attn_ckpt_version="mix",
            weight_dtype=init_weight_dtype(PRECISION),
            use_tf32=True,
            device="cuda",
        )
        _mask_processor = VaeImageProcessor(
            vae_scale_factor=8, do_normalize=False,
            do_binarize=True, do_convert_grayscale=True,
        )
        _automasker = AutoMasker(
            densepose_ckpt=os.path.join(repo_path, "DensePose"),
            schp_ckpt=os.path.join(repo_path, "SCHP"),
            device="cuda",
        )


def run_tryon(
    person_path: str,
    garment_path: str,
    cloth_type: str = "upper",   # "upper" (shirts/tops), "overall" (dresses)
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    seed: int = DEFAULT_SEED,
) -> str:
    """Run one try-on and return the path of the generated image."""
    from utils import resize_and_crop, resize_and_padding

    if _pipeline is None:
        load_model()

    try:
        person = Image.open(person_path).convert("RGB")
        garment = Image.open(garment_path).convert("RGB")
    except Exception:
        raise TryOnError(
            "BAD_IMAGE",
            "We could not read this image. Please upload a clearer photo.",
        )

    with _lock:  # only one GPU job at a time
        try:
            person = resize_and_crop(person, (WIDTH, HEIGHT))
            garment = resize_and_padding(garment, (WIDTH, HEIGHT))

            mask = _automasker(person, cloth_type)["mask"]
            mask = _mask_processor.blur(mask, blur_factor=9)

            generator = None
            if seed != -1:
                generator = torch.Generator(device="cuda").manual_seed(seed)

            result = _pipeline(
                image=person,
                condition_image=garment,
                mask=mask,
                num_inference_steps=steps,
                guidance_scale=cfg,
                generator=generator,
            )[0]

            out_path = RESULTS_DIR / f"{uuid.uuid4().hex}.png"  # random ID
            result.save(out_path)
            return str(out_path)

        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            raise TryOnError(
                "OUT_OF_MEMORY",
                "We could not generate the result. Try another image or product.",
            )
        except TryOnError:
            raise
        except Exception:
            torch.cuda.empty_cache()
            raise TryOnError(
                "GENERATION_FAILED",
                "We could not generate the result. Try another image or product.",
            )