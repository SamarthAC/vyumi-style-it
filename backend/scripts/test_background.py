"""
Try the studio backdrops on an existing try-on result. No GPU or model needed.

Usage (from the repo root, with the catvton env active):
    python backend/scripts/test_background.py path\\to\\result.png
    python backend/scripts/test_background.py path\\to\\result.png studio_ivory
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image

from backend.services import background_service as bg

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

src = Path(sys.argv[1])
names = [sys.argv[2]] if len(sys.argv) > 2 else [n for n in bg.list_backdrops() if n != bg.ORIGINAL]

out_dir = Path(__file__).resolve().parents[1] / "data" / "results"
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(src).convert("RGB")
for name in names:
    t0 = time.time()
    out = bg.apply_backdrop(img, name)
    path = out_dir / f"bg_{name}_{src.stem}.png"
    out.save(path)
    print(f"{name}: {time.time() - t0:.1f}s -> {path}")