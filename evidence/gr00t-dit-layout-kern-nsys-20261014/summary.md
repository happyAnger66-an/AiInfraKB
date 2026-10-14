# GR00T DiT layout kernels — nsys root cause (2026-10-14)

- Machine: Thor 2239 thor-001 / pi05-forge-agent; gate PASS (gpc 1575 / nvd 1692)
- Stage: denoise_loop; W3+I10; nsys cuda + cuda-graph=node
- Base: `/work/gr00t_n17_xdof_fp16_v2_vit_llm_flash_unirt`
- Cand: `/work/gr00t_n17_xdof_fp16_v2_dit_layout_kern_unirt` + `MLC_VLA_GR00T_DIT_LAYOUT=1`

## Result

| metric | base | cand | Δ |
|---|---:|---:|---:|
| GPU ms/infer | 72.65 | 72.09 | −0.56 |
| layout+pack ms | 8.25 | 8.82 | +0.57 |
| tensor_core ms | 55.27 | 54.11 | −1.16 (L 1060 flat) |
| fused layout family → pack | 6.01 | 6.56 | +0.55 |

**Root cause:** Tensor Core path intact (same nvjet/cutlass set). Hand-written `dit_pack_{k,v}` SIMT is slower than TVM `fused_reshape*transpose*cast`; no launch reduction (844→852).

Artifacts: `nsys_rootcause.json`, `nsys_compare.json`, kernel CSVs. Thor reps: `/home/nvidia/pi05_forge_work/gr00t_nsys_dit_layout_cmp/`.
