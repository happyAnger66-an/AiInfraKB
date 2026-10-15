# Current speed baseline (GR00T N1.7 FP8)

- Updated: 2026-10-15T11:20:00+08:00
- Stack: **L1 + L3 + LlmRmsQ + EncFp8 + D1 + crosskv + D1take + AdaStatic + Cg4**
- e2e_full target band: **~90–91 ms** (lockfreq)

## Packs

| role | path |
|---|---|
| backbone (L1+L3+LlmRmsQ+EncFp8) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_i4_unirt` |
| backbone (alias) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQEnc_unirt` → same |
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
- preset `e4m3_gr00t_llm_l3_qkv_enc`（136 = L3+QKV 112 + VL-SA Enc 24）(**EncFp8**)
- AttnScore / DIT_LAYOUT: **off**
- state_encoder / vlln: **未动**

## Evidence

- Merge: `gr00t-cg4-merge.md`（Cg4；same-session e2e −6.14 / loop −5.63；bit-identical）
- Prior: `gr00t-encfp8-merge.md`（pre-Cg4 e2e_full 95.513）
- Git: mlc-vla tip Cg4（见 merge 报告 SHA）；pushed `r/feat/gelu-fp8-synapsex`

## Merge sanity (lockfreq, this update)

| stage | median ms |
|---|---:|
| embed_vision | 19.307 |
| backbone_llm | 18.417 |
| encode_condition | 5.203 |
| denoise_loop | 43.540 |
| e2e_head | 52.998 |
| **e2e_full** | **90.295** |

Accuracy vs pre-Cg4 AdaStatic DiT: cos=1.0, mse=0.0, mean_abs=0.0, PASS=True（bit-identical；132/132）。
Δ vs same-session AdaStatic ref: e2e_full −6.140 / denoise_loop −5.633 / denoise_step −2.513。
