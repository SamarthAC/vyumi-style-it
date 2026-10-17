import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
import torch
import tryon_service as t

if len(sys.argv) < 3:
    print("Usage: python backend/scripts/test_tryon.py person.jpg garment.jpg [upper|overall]")
    sys.exit(1)

cloth_type = sys.argv[3] if len(sys.argv) > 3 else "upper"

t0 = time.time()
t.load_model()
print(f"Model loaded in {time.time() - t0:.1f}s")

for i in range(2):  # 1st run = warm-up, 2nd = real timing
    t1 = time.time()
    out = t.run_tryon(sys.argv[1], sys.argv[2], cloth_type)
    print(f"Run {i+1}: {time.time() - t1:.1f}s -> {out}")

print(f"Peak VRAM: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")