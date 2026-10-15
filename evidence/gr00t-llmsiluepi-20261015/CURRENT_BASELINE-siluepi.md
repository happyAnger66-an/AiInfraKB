# Current speed baseline (GR00T N1.7 FP8)

- Updated: 2026-10-15T11:32:00+08:00
- Stack: **L1 + L3 + LlmRmsQ + EncFp8 + D1 + crosskv + D1take + AdaStatic + Cg4 + LlmSiluEpi**
- e2e_full target band: **~89–90 ms** (lockfreq)

## Packs

| role | path |
|---|---|
| backbone (L1+L3+LlmRmsQ+EncFp8+LlmSiluEpi) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_i4_unirt` |
| backbone (alias) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQEnc_unirt` / `..._SiluMul_unirt` → same |
| backbone (pre-SiluMul Enc) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQEnc_pre_SiluMul_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_i4_unirt` |
| backbone (prior LlmRmsQ only) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_pre_EncFp8_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_i4_unirt` |
| backbone (prior L1+L3 only) | `gr00t_n17_bb_fp8_baseline_L1L3_pre_LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_o_down_i4_unirt` |
| DiT (canonical) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` → `..._adastatic_cg4_unirt` |
| DiT (Cg4 alias) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_Cg4_unirt` → same |
| DiT (pre-Cg4) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_pre_Cg4_unirt` → `..._take_fuse_adastatic_unirt` |
| DiT (raw Cg4) | `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_cg4_unirt` |

## Source defaults (compile-time)

- `MLC_VLA_GR00T_ADA_LN_PRECOMP=1` (D1)
- `MLC_VLA_GR00T_CROSS_KV_PRECOMP=1`
- `MLC_VLA_GR00T_ADA_LN_BANK_STEP=1` (**D1take**)
- `MLC_VLA_GR00T_ADA_LN_STATIC=1` / `--set static_ada_ln_bank=true` (**AdaStatic**)
- **`--cuda-graph`** on denoise compile (**Cg4**；`num_inference_timesteps=4`；**禁 2-step**)
- `MLC_VLA_GR00T_LLM_RMS_FP8=1` + `MLC_VLA_GR00T_LLM_QKV_SHARED_FP8=1` + O/DOWN FP8 (**LlmRmsQ** on L3)
- `MLC_VLA_GR00T_LLM_SILU_MUL_FP8=1` + `MLC_VLA_SILU_MUL_FP8_SO=libsynapsex_silu_mul_fp8.so` (**LlmSiluEpi**)
- preset `e4m3_gr00t_llm_l3_qkv_enc`（136 = L3+QKV 112 + VL-SA Enc 24）(**EncFp8**)
- AttnScore / DIT_LAYOUT: **off**
- state_encoder / vlln: **未动**；**禁** merge gate_up / Silu GEMM-epi

## Evidence

- Merge: `gr00t-llmsiluepi-merge.md`（LlmSiluEpi；same-session e2e −0.438 / llm −0.646；gate PASS）
- Prior: `gr00t-cg4-merge.md`（pre-SiluMul e2e_full 90.295）
- Git: synapsex `feat/silu-mul-fp8` + mlc-vla `feat/gelu-fp8-synapsex`（见 merge 报告 SHA）

## Merge sanity (lockfreq, this update)

| stage | median ms |
|---|---:|
| embed_vision | 19.338 |
| backbone_llm | 17.619 |
| encode_condition | 5.119 |
| denoise_loop | 43.953 |
| e2e_head | 52.401 |
| **e2e_full** | **89.772** |

Accuracy vs Cg4 lock bb: cos=0.999952, mse=1.15e-4, mean_abs=4.54e-3, PASS=True（120/132 per-dim）。
Δ vs same-session Cg4 ref: e2e_full −0.438 / backbone_llm −0.646。
