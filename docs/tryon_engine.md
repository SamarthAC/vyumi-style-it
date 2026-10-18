# System Specification and Quick Setup

- Model: CatVTON (CC BY-NC-SA 4.0, non-commercial)
- GPU: RTX 4060 8 GB, bf16, 1024x768
- Python 3.9 with torch 2.4.0+cu121
- Install matplotlib through conda
- Pin diffusers==0.30.0, pydantic==2.10.6, and upgrade accelerate
- Launch from Anaconda Prompt with set CUDA_VISIBLE_DEVICES=0
- Results table and known limitation

# CatVTON Try-On Test Results

**Model:** CatVTON (CC BY-NC-SA 4.0, non-commercial, prototype only)
**GPU:** RTX 4060 8 GB | **Precision:** bf16 | **Resolution:** 1024x768
**Tested by:** <your name> | **Date:** 2026-10-17

| #   | Person photo                  | Garment       | Time (s) | Peak VRAM (GB) | Quality | Notes                           |
| --- | ----------------------------- | ------------- | -------- | -------------- | ------- | ------------------------------- |
| 1   | person_01 (front, good light) | white_tshirt  | 59.7s    | 4.89 GB        | Bad     | Baseline case                   |
| 2   | person_02 (front, good light) | blue_shirt    | 58.7s    | 4.88 GB        | Good    |                                 |
| 3   | person_03 (slight angle)      | black_top     | 60.5s    | 4.89 GB        | Bad     | Potential NSFW content Detected |
| 4   | person_01                     | striped_shirt | 59.5s    | 4.89 GB        | Okay    | Pattern test                    |
| 5   | person_02                     | printed_tee   | 59.5s    | 4.88 GB        | Good    | Logo/print test                 |
| 6   | person_03                     | dress_01      | 59.2s    | 4.88 GB        | Good    | Dress test                      |

## Quality scale

- **Good:** garment clearly recognizable, natural fit, no visible artifacts
- **Okay:** garment recognizable but with small errors (edges, hands, color shift)
- **Bad:** wrong garment, distorted body, or failed

## Summary

- Average time per image: _59.2_ s
- Peak VRAM seen: _4.89_ GB
- Good / Okay / Bad count: _3_ / _1_ / _2_

## Known limitations

- NFSW Content is being detected for slightest exposure in the dress
- Cannot properly scale out the upper part
