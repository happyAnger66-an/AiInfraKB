# Current speed baseline (GR00T N1.7 FP8)

- Updated: 2026-10-15T12:45:00+08:00
- Stack: **L1 + L3 + LlmRmsQ + EncFp8 + D1 + crosskv + D1take + AdaStatic + Cg4 + LlmSiluEpi + DitSoftAdd**
- e2e_full target band: **~87–88 ms** (lockfreq)

## Packs

| role | path |
|---|---|
| backbone (L1+L3+LlmRmsQ+EncFp8+LlmSiluEpi) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_i4_unirt` |
| DiT (canonical) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` → `..._cg4_softadd_unirt` |
| DiT (Cg4+SoftAdd alias) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_Cg4_unirt` / `..._Cg4_SoftAdd_unirt` → same |
| DiT (pre-SoftAdd Cg4) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_Cg4_pre_SoftAdd_unirt` → `..._adastatic_cg4_unirt` |
| DiT (raw SoftAdd) | `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_cg4_softadd_unirt` |

## Source defaults (compile-time)

- `MLC_VLA_GR00T_ADA_LN_PRECOMP=1` (D1)
- `MLC_VLA_GR00T_CROSS_KV_PRECOMP=1`
- `MLC_VLA_GR00T_ADA_LN_BANK_STEP=1` (**D1take**)
- `MLC_VLA_GR00T_ADA_LN_STATIC=1` / `--set static_ada_ln_bank=true` (**AdaStatic**)
- **`--cuda-graph`** on denoise compile (**Cg4**；`num_inference_timesteps=4`；**禁 2-step**)
- `MLC_VLA_GR00T_LLM_RMS_FP8=1` + `MLC_VLA_GR00T_LLM_QKV_SHARED_FP8=1` + O/DOWN FP8 (**LlmRmsQ** on L3)
- `MLC_VLA_GR00T_LLM_SILU_MUL_FP8=1` + `MLC_VLA_SILU_MUL_FP8_SO=libsynapsex_silu_mul_fp8.so` (**LlmSiluEpi**)
- **`MLC_VLA_GR00T_DIT_SOFTADD=1`** (**DitSoftAdd**；`flashrt.res_ln_fp8`)
- preset `e4m3_gr00t_llm_l3_qkv_enc`（EncFp8）
- AttnScore / DIT_LAYOUT: **off**
- **禁** DitGemm 本轮；**禁** QK/softmax/PV

## Evidence

- Merge: `gr00t-ditsoftadd-merge.md`（DitSoftAdd；same-session e2e −0.649 / loop −1.639；gate bit-identical PASS）
- Prior: `gr00t-llmsiluepi-merge.md`（pre-SoftAdd e2e_full 89.772）
- Git: mlc-vla `feat/gelu-fp8-synapsex`（见 merge 报告 SHA）

## Merge sanity (lockfreq, this update)

| stage | median ms |
|---|---:|
| embed_vision | 19.206 |
| backbone_llm | 17.664 |
| encode_condition | 5.094 |
| denoise_loop | 42.610 |
| e2e_head | 51.622 |
| **e2e_full** | **87.506** |

Accuracy vs Cg4 lock DiT: cos=1.0 / mse=0 / mean_abs=0, PASS=True（132/132 per-dim）。
Δ vs same-session Cg4+SiluEpi ref: e2e_full **−0.649** / denoise_loop **−1.639**。
