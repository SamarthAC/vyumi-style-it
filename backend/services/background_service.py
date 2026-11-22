"""
Studio-backdrop compositing for VYUMI "Style It Your Way".

Takes a finished try-on image, cuts the person out, and places them on a clean
studio backdrop with a soft shadow. This is compositing, not generation: the
person's pixels are kept as they are, so nothing new is "invented".

Person cut-out uses rembg (MIT). The model weights download on first use.
If rembg is missing or fails, the caller should fall back to the original
background (tryon_service does this).

Backdrops:
  - built-in presets (generated with Pillow, no image assets needed)
  - any .jpg/.png you drop into backend/data/backdrops/ (name = file name)
"""
import threading
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageFilter, ImageOps

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKDROP_DIR = REPO_ROOT / "backend" / "data" / "backdrops"

ORIGINAL = "original"

# name -> (top colour, bottom colour)
PRESETS = {
    "studio_ivory": ((243, 238, 228), (222, 213, 198)),
    "studio_grey": ((232, 233, 235), (190, 193, 198)),
    "studio_blush": ((246, 232, 230), (226, 200, 197)),
    "studio_charcoal": ((92, 94, 98), (44, 45, 48)),
}

# Tuning knobs
ERODE_SIZE = 3          # odd number; shrinks the cut-out edge to remove old-background halo
EDGE_BLUR = 1.5         # softens the cut-out edge
SHADOW_STRENGTH = 0.22  # 0 = no shadow
SHADOW_BLUR = 16
SHADOW_OFFSET = 12      # px downwards
VIGNETTE_STRENGTH = 0.16

_session = None
_session_lock = threading.Lock()


def list_backdrops() -> List[str]:
    names = [ORIGINAL] + list(PRESETS)
    if BACKDROP_DIR.exists():
        for p in sorted(BACKDROP_DIR.iterdir()):
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                names.append(p.stem)
    return names


def make_backdrop(name: str, size) -> Image.Image:
    """Return an RGB backdrop of the given (width, height)."""
    w, h = size
    if name in PRESETS:
        top, bottom = PRESETS[name]
        grad = Image.linear_gradient("L").resize((w, h))  # black at top -> white at bottom
        base = Image.composite(
            Image.new("RGB", size, bottom), Image.new("RGB", size, top), grad
        )
        # gentle vignette so the backdrop doesn't look flat
        radial = Image.radial_gradient("L").resize((w, h))  # black centre -> white edges
        vig = radial.point(lambda p: int(p * VIGNETTE_STRENGTH))
        return Image.composite(Image.new("RGB", size, (0, 0, 0)), base, vig)

    if BACKDROP_DIR.exists():
        for p in BACKDROP_DIR.iterdir():
            if p.stem == name and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                return ImageOps.fit(Image.open(p).convert("RGB"), size, Image.LANCZOS)

    raise ValueError(f"Unknown backdrop: {name!r}. Available: {list_backdrops()}")


def _person_mask(image: Image.Image) -> Image.Image:
    """Cut-out mask (mode L, white = person) from rembg's human-segmentation model."""
    global _session
    try:
        from rembg import new_session, remove
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "rembg is not installed. Run: python -m pip install rembg onnxruntime"
        ) from e

    with _session_lock:
        if _session is None:
            _session = new_session("u2net_human_seg")
        mask = remove(image, session=_session, only_mask=True, post_process_mask=True)
    return mask.convert("L")


def apply_backdrop(
    image: Image.Image, name: str, mask: Optional[Image.Image] = None
) -> Image.Image:
    """
    Place the person from `image` on the named backdrop.
    `mask` (mode L, white = person) can be passed in; otherwise it is computed.
    """
    if not name or name == ORIGINAL:
        return image

    image = image.convert("RGB")
    size = image.size
    alpha = (mask or _person_mask(image)).convert("L").resize(size)

    # clean the edge: erode a little, then soften
    if ERODE_SIZE > 1:
        alpha = alpha.filter(ImageFilter.MinFilter(ERODE_SIZE))
    alpha = alpha.filter(ImageFilter.GaussianBlur(EDGE_BLUR))

    backdrop = make_backdrop(name, size)

    # soft shadow behind/below the person to ground them on the backdrop
    if SHADOW_STRENGTH > 0:
        shadow = Image.new("L", size, 0)
        blurred = alpha.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)).point(
            lambda p: int(p * SHADOW_STRENGTH)
        )
        shadow.paste(blurred, (0, SHADOW_OFFSET))
        backdrop = Image.composite(Image.new("RGB", size, (0, 0, 0)), backdrop, shadow)

    return Image.composite(image, backdrop, alpha)