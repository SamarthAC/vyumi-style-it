"""
Try-on engine service for VYUMI 'Style It Your Way'.
Integrates CatVTON engine contract:
    - load_model()
    - run_tryon(person_path, garment_path, cloth_type="upper") -> result_path
    - TryOnError(code, message)
"""
import os
import sys
import threading
import uuid
import logging
from pathlib import Path
from typing import Optional, Callable
from PIL import Image

logger = logging.getLogger("vyumi.tryon")

REPO_ROOT = Path(__file__).resolve().parents[2]
CATVTON_DIR = REPO_ROOT / "third_party" / "CatVTON"
RESULTS_DIR = REPO_ROOT / "backend" / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Prepend CatVTON dir to sys.path if it exists
if CATVTON_DIR.exists():
    sys.path.insert(0, str(CATVTON_DIR))

# --- Settings ---
BASE_MODEL = "booksforcharlie/stable-diffusion-inpainting"
CHECKPOINT_REPO = "zhengchong/CatVTON"
PRECISION = os.environ.get("TRYON_PRECISION", "bf16")
WIDTH, HEIGHT = 768, 1024
DEFAULT_STEPS = 50
DEFAULT_CFG = 2.5
DEFAULT_SEED = 42

class TryOnError(Exception):
    """Exception raised by the try-on engine with code and human-readable message."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def __repr__(self):
        return f"TryOnError(code={self.code!r}, message={self.message!r})"


# Internal state
_pipeline = None
_automasker = None
_mask_processor = None
_lock = threading.Lock()
_load_lock = threading.Lock()

_engine_ready: bool = False
_engine_error: Optional[TryOnError] = None

# Optional mock runner for non-GPU / test execution
_custom_runner: Optional[Callable[..., str]] = None
_custom_loader: Optional[Callable[[], None]] = None


def set_custom_engine(loader: Optional[Callable[[], None]] = None, runner: Optional[Callable[..., str]] = None, mark_ready: Optional[bool] = None):
    """Set custom engine loader and runner (primarily used for automated testing without GPU)."""
    global _custom_loader, _custom_runner, _engine_ready, _engine_error
    _custom_loader = loader
    _custom_runner = runner
    if mark_ready is not None:
        _engine_ready = mark_ready
    else:
        _engine_ready = (runner is not None or loader is None)
    _engine_error = None


def reset_custom_engine():
    """Reset custom test hooks."""
    global _custom_loader, _custom_runner, _engine_ready, _engine_error, _pipeline
    _custom_loader = None
    _custom_runner = None
    _engine_ready = False
    _engine_error = None
    _pipeline = None


def is_engine_ready() -> bool:
    """Check if try-on engine was successfully loaded and is ready for inference."""
    return _engine_ready


def get_engine_error() -> Optional[TryOnError]:
    """Retrieve initialization error if engine failed to load."""
    return _engine_error


def load_model():
    """
    Initialize try-on model at application startup.
    Ensures model is loaded once and safe to call multiple times.
    Raises TryOnError if initialization fails (e.g., NO_GPU, missing dependencies, or weights).
    """
    global _pipeline, _automasker, _mask_processor, _engine_ready, _engine_error

    with _load_lock:
        if _engine_ready:
            return

        if _custom_loader is not None:
            try:
                _custom_loader()
                _engine_ready = True
                _engine_error = None
                return
            except TryOnError as e:
                _engine_ready = False
                _engine_error = e
                raise
            except Exception as e:
                err = TryOnError("INIT_FAILED", f"Engine failed to load: {str(e)}")
                _engine_ready = False
                _engine_error = err
                raise err

        # Real CatVTON loading
        try:
            import torch
            if not torch.cuda.is_available():
                err = TryOnError("NO_GPU", "No GPU found for the try-on engine.")
                _engine_ready = False
                _engine_error = err
                raise err

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
            _engine_ready = True
            _engine_error = None

        except TryOnError as e:
            _engine_ready = False
            _engine_error = e
            raise
        except Exception as e:
            err = TryOnError("INIT_FAILED", f"Unexpected initialization error: {str(e)}")
            _engine_ready = False
            _engine_error = err
            raise err


def run_tryon(
    person_path: str,
    garment_path: str,
    cloth_type: str = "upper",  # "upper" (shirts/tops), "overall" (dresses)
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    seed: int = DEFAULT_SEED,
) -> str:
    """
    Run one virtual try-on inference and return the generated image path.
    Only one GPU/inference job runs at a time via threading.Lock.
    """
    global _pipeline

    # Custom runner for testing/mocking
    if _custom_runner is not None:
        with _lock:
            return _custom_runner(
                person_path=person_path,
                garment_path=garment_path,
                cloth_type=cloth_type,
                steps=steps,
                cfg=cfg,
                seed=seed
            )

    # Validate engine readiness
    if not _engine_ready or _pipeline is None:
        if _engine_error is not None:
            raise _engine_error
        load_model()

    # Image validation
    try:
        person = Image.open(person_path).convert("RGB")
        garment = Image.open(garment_path).convert("RGB")
    except Exception:
        raise TryOnError(
            "BAD_IMAGE",
            "We could not read this image. Please upload a clearer photo.",
        )

    import torch
    from utils import resize_and_crop, resize_and_padding

    with _lock:  # Serialized execution
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

            out_path = RESULTS_DIR / f"{uuid.uuid4().hex}.png"
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
