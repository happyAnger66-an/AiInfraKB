# Evidence: GR00T DiT FP8 quantize-tax / fused e4m3-out (2026-10-14)

Source agent: 牛马 @ LT5CG3344QDF / Thor lockfreq.
Ingested by: 知识库/box → AiInfraKB inbox (not cards).

## Key measured numbers (phase_ada_ln vs FP16 temb_fix)

- e2e_full p50: 137.732 → 121.434 ms (**1.134×**)
- denoise_loop p50: 76.996 → 60.915 ms (**1.264×**)
- denoise_step p50: 20.065 → 16.129 ms (**1.244×**)
- quantize tax (full_dit no-fuse → +ada_ln): ~15%+ → **1.64% / 0.225 ms** (denoise_step share)
- accuracy dims0–31: phase_ada_ln **26/32**; qkv24 reference **32/32**

## Files

| file | role |
|---|---|
| baseline-snapshot.md | dual-delivery standing snapshot |
| accuracy-report.md | overall + per-dim tables |
| reuse-draft.md | KB ingest source draft |
| quantize-tax-plan.md | tax analysis / plan |
| ada-ln-fp8-design.md | AdaLN FP8 design |
| precision-map.png | precision coverage map |
| stages_*.json | hybrid stage timings |
| full_dit_phase_ada_ln_speed_report.json | speed report |
| fp8_*_gate_with_mabs.json | accuracy gates |

## Code anchors (company GitLab only)

- synapsex `feat/ada-ln-fp8` @ `1ff9653`; gelu @ `0cd45c0`
- mlc-vla `feat/gelu-fp8-synapsex` @ `2dd3cf0`
