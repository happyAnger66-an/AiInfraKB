# GR00T LlmSiluEpi merge — FlashRT silu_mul_split glue（synapsex so → Qwen3MLP）

- Date: 2026-10-15 11:32 Asia/Shanghai
- Status: **MERGED**；基线指针已更新；**已 push**（见 Commit）
- Prior scout: `gr00t-llmsiluepi-design-scout.md`（Soft-GO → 架构师升 **GO glue**；估 −0.3～−1.0；**不挖 GEMM-epi**）
- This merge: **LlmSiluEpi** = synapsex `silu_mul_fp8` 薄 so（对齐 FlashRT `silu_mul_split_fp8_fp16`）+ mlc-vla `Qwen3MLP` 接线

---

## 合入状态：**DONE**

| 项 | 值 |
|---|---|
| Stack | **L1 + L3 + LlmRmsQ + EncFp8 + D1 + crosskv + D1take + AdaStatic + Cg4 + LlmSiluEpi** |
| bb (canonical) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_i4_unirt` |
| bb (alias) | `..._L1L3LlmRmsQEnc_unirt` / `..._SiluMul_unirt` → same |
| bb (pre-SiluMul) | `..._L1L3LlmRmsQEnc_pre_SiluMul_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_i4_unirt` |
| DiT (unchanged Cg4) | `..._adastatic_cg4_unirt` |
| CURRENT_BASELINE | `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` + shared 已升本栈 |
| so | `/work/phase_a_so/libsynapsex_silu_mul_fp8.so`（ABI `synapsex_silu_mul_fp8`） |

Compile/runtime env（bb）：既有 LlmRmsQ+Enc 全套 + `MLC_VLA_GR00T_LLM_SILU_MUL_FP8=1` + `MLC_VLA_SILU_MUL_FP8_SO=...`。

**禁** merge gate_up；**禁** 新 Silu GEMM epi（本轮 NO）。

---

## Sanity（锁频，warmup=8 iters=40；vs same-session Cg4 lock）

| stage | Cg4 lock ref | **+LlmSiluEpi** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.260 | 19.338 | +0.077 |
| **backbone_llm** | **18.265** | **17.619** | **−0.646** |
| encode_condition | 5.123 | 5.119 | −0.004 |
| denoise_step | 13.426 | 13.911 | +0.485 |
| denoise_loop | 43.261 | 43.953 | +0.692 |
| e2e_head | 53.617 | 52.401 | −1.216 |
| **e2e_full** | **90.210** | **89.772** | **−0.438** |

### vs scout 对照

| | scout 估 | **merge sanity** |
|---|---:|---:|
| Δbackbone_llm | −0.3～−1.0 | **−0.646** |
| Δe2e_full | −0.3～−1.0 | **−0.438** |
| 量级 | 同档 | 同档（落保守带中） |

相对锁基线旧值 90.295：本 merge session 的 Cg4 ref 抖到 90.210；**合入后权威墙钟以本表 cand = 89.772 为准**（≈11.14 Hz）。距 66.7 仍 ~23.1 ms。

> denoise_loop +0.69 / step +0.48：DiT 未改，记会话噪声；刀收益以 **backbone_llm −0.646** / **e2e_full −0.438** 为准。

### Accuracy（denoise_loop actions，vs Cg4 lock bb）

| | value | gate |
|---|---:|---|
| overall cos | **0.999952** | >0.999 ✅ |
| overall mse | **1.152e-04** | <0.0005 ✅ |
| overall mean_abs | **4.543e-03** | — |
| per-dim pass | **120 / 132** | report |
| backbone_llm cos | 0.8437 | soft（静态 Q 进 silu 核，非 bit-identical） |

完整 per-dim：`llmsiluepi_merge_gate_vs_cg4.json`。

---

## Git commit

| repo | branch | SHA | message（首行） | push |
|---|---|---|---|---|
| `synapsex` | `feat/silu-mul-fp8` | `06783a8e8384cfaf0edf687a1be30a0e236a61fa` | `feat(silu_mul_fp8): SiLU(gate)*up→e4m3 通用 so（FlashRT silu_mul_split）` | **已 push** → `origin` |
| `mlc-vla` | `feat/gelu-fp8-synapsex` | `ad3cc2bac2a4198d95fc036c1d2c9005a47f52d9` | `feat(llm): LlmSiluEpi silu_mul_fp8 glue（FlashRT split → down.prequant）` | **已 push** → `r` |

### Files

**synapsex**
- `operators/silu_mul_fp8/*`、`scripts/build_silu_mul_fp8.sh`、`scripts/run_silu_mul_fp8_tests.sh`
- `tests/silu_mul_fp8/test_correctness.cu`
- `CONTRACT.md` / `docs/catalog.json` / `deploy/env.sh`

**mlc-vla**
- `python/mlc_vla/kernels/flashrt/silu_mul_fp8.cuh`（synapsex-first + local fallback）
- `python/mlc_vla/kernels/flashrt/shim.cu` / `__init__.py`（`flashrt_silu_mul_fp8`）
- `python/mlc_vla/model/gr00t_n17/modules_llm.py`（`Qwen3MLP.forward` 优先 silu_mul_fp8）

未碰 unirt / DitSoftAdd / GEMM-epi。

---

## Artifacts

- Report: `/home/nio/shared/gr00t-fp8/gr00t-llmsiluepi-merge.md`
- Thor: `/work/gr00t_fp8_phase_a/llmsiluepi_merge_bench/measure_summary.json`
- Pack bb: `/work/gr00t_fp8_phase_a/gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_i4_unirt`
- so: `/work/phase_a_so/libsynapsex_silu_mul_fp8.so`
- Scout: `gr00t-llmsiluepi-design-scout.md`
- Gate: `llmsiluepi_merge_gate_vs_cg4.json`

## 建议

LlmSiluEpi **GO glue 已合**；e2e_full **~89.8 ms**。不自批下一刀。
