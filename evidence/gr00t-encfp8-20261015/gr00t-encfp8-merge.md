# GR00T EncFp8 merge — 叠入 L1+L3+LlmRmsQ+D1+crosskv+D1take+AdaStatic

- Date: 2026-10-15 10:59 Asia/Shanghai
- Status: **MERGED**；基线指针已更新
- Prior scout: `gr00t-encfp8-scout.md`（Soft-GO → 架构师升 **GO**；encode −1.39 / e2e −0.41 isolate）
- This merge: **EncFp8** = VL-SA 4×BasicTransformerBlock 静态 FP8，叠在 **LlmRmsQ** 锁基线上

---

## 合入状态：**DONE**

| 项 | 值 |
|---|---|
| Stack | **L1 + L3 + LlmRmsQ + EncFp8 + D1 + crosskv + D1take + AdaStatic** |
| bb (canonical) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_i4_unirt` |
| bb (alias) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQEnc_unirt` → same |
| bb (prior LlmRmsQ) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_pre_EncFp8_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_i4_unirt` |
| DiT (unchanged) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` → `..._take_fuse_adastatic_unirt` |
| CURRENT_BASELINE | `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` + shared 已升本栈 |
| preset | `e4m3_gr00t_llm_l3_qkv_enc`（136 = L3+QKV 112 + VL-SA 24） |

Compile/runtime env（bb）：`LLM_RMS_FP8=1` + `LLM_QKV_SHARED_FP8=1` + L3 O/DOWN + Enc VL-SA FP8 glue（QKV-shared / gelu_fp8 / FFN_LN_FP8 / attn-out）。

**state_encoder / vlln 本轮不挖。**

---

## Sanity（锁频，warmup=8 iters=40；vs 当前锁 LlmRmsQ+AdaStatic）

| stage | LlmRmsQ lock | **+EncFp8** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.530 | 19.083 | -0.448 |
| backbone_llm | 18.459 | 18.568 | +0.109 |
| encode_condition | 6.615 | 5.177 | -1.438 |
| denoise_step | 16.047 | 16.464 | +0.417 |
| denoise_loop | 50.788 | 49.714 | -1.074 |
| e2e_head | 60.380 | 58.667 | -1.713 |
| e2e_full | 98.244 | 95.513 | -2.731 |

### vs scout 对照

| | scout (vs L3, Enc isolate) | **merge sanity (vs LlmRmsQ)** |
|---|---:|---:|
| Δencode_condition | −1.388 | **-1.438** |
| Δe2e_full | −0.407 | **-2.731** |
| 量级 | encode 同档 | encode 同档；e2e 本 session 额外吃到 denoise/head 噪声利好 |

相对锁基线旧值 98.432：本 merge session 的 LlmRmsQ ref 抖到 98.244；**合入后权威墙钟以本表 cand = 95.513 为准**（≈10.47 Hz）。距 66.7 仍 ~28.8 ms。

> denoise_loop -1.074 / e2e_head -1.713：DiT 未改，记会话噪声；刀收益以 **encode_condition -1.438** 为准。

### Accuracy（denoise_loop actions，vs pre-merge LlmRmsQ bb）

| | value | gate |
|---|---:|---|
| overall cos | **0.999999** | >0.999 ✅ |
| overall mse | **2.723e-06** | <0.0005 ✅ |
| overall mean_abs | **1.202e-03** | — |
| isolate cos/mse | 0.999999 / 2.723e-06 | PASS |
| per-dim pass | **126/132** | report |
| backbone_llm cos (LlmRmsQ vs cand) | 1.0000 | bit-identical（Enc 未动 LLM） |
| encode_vl isolate cos | 0.9989 | soft feature |

完整 per-dim：`encfp8_merge_bench/gate_vs_llmrmsq.json`。

---

## Git commit

| | |
|---|---|
| Repo | `mlc-vla`（`feat/gelu-fp8-synapsex` / r-infra） |
| Scope | **仅 EncFp8 presets**（`e4m3_gr00t_enc` / `e4m3_gr00t_llm_l3_enc` / `e4m3_gr00t_llm_l3_qkv_enc` + VL-SA patterns） |
| **不含** | LlmRmsQ（已在 `2d0df4e`；本 commit 不混入） |
| Push | `r/feat/gelu-fp8-synapsex` @ `7d9fd34` |
| SHA | `7d9fd34cd3bbd9d71d36413a5775a7aa672aff22` |

---

## Artifacts

- Report: `/home/nio/shared/gr00t-fp8/gr00t-encfp8-merge.md`
- Thor: `/work/gr00t_fp8_phase_a/encfp8_merge_bench/measure_summary.json`
- Pack bb: `/work/gr00t_fp8_phase_a/gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_i4_unirt`
- Alias: `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` / `...LlmRmsQEnc_unirt`
- Scout: `gr00t-encfp8-scout.md`
