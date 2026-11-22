import sys
import time
from pathlib import Path

# Make "backend" importable when run from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import torch
from backend.services import tryon_service as t

if len(sys.argv) < 3:
    print("Usage: python backend/scripts/test_tryon.py person.jpg garment.jpg [upper|overall] [seed]")
    sys.exit(1)

person, garment = sys.argv[1], sys.argv[2]
cloth_type = sys.argv[3] if len(sys.argv) > 3 else "upper"
seed = int(sys.argv[4]) if len(sys.argv) > 4 else t.DEFAULT_SEED

t0 = time.time()
t.load_model()
print(f"Model loaded in {time.time() - t0:.1f}s")

for i in range(2):  # run 1 = warm-up, run 2 = real timing
    t1 = time.time()
    out = t.run_tryon(person, garment, cloth_type, seed=seed)
    print(f"Run {i + 1}: {time.time() - t1:.1f}s -> {out}")

print(f"Peak VRAM (PyTorch only): {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")