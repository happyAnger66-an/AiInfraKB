# GR00T EncFp8 — encode_condition VL-SA FP8 scout

- Date: 2026-10-15 Asia/Shanghai (~10:50)
- Status: **wired + compiled + lockfreq staged + gate + nsys A/B**; overall gate **PASS**；**默认不合**
- Hill gate: overall **cos>0.999 AND mse<0.0005** (per-dim report-only)
- Steering: quant / fusion / ops / precompute only — **no** 2-step; **禁止** L2 / V1 / AttnScore / DitAttnE4 核债重开；Vision Soft-GO backlog 本轮不抢
- Thor: `pi05-forge-agent` / thor-001; work `/work/gr00t_fp8_phase_a/`
- Baseline stack: **L1+L3+D1+crosskv+D1take+AdaStatic**（锁 ~99.35；same-session L3 ref **98.656**）
- LlmRmsQ 合入未进本刀对照（隔离 EncFp8）

---

## Verdict

| | |
|---|---|
| **Go / no-go** | **Soft-GO（默认不合）** |
| Speed | **WIN（encode）** — encode_condition **−1.388 ms**；e2e_full **−0.407 ms**（其它 stage 会话噪声吃掉部分） |
| overall gate | **PASS** cos **0.999979** / mse **5.03e-5**（isolate cos **0.999993** / mse **1.67e-5**） |
| encode feature cos | **~0.9988** soft（isolate VL-SA）；state 未动 |
| nsys | **HIT** `fp8_gemm`×480；`gelu_fp8`×80；`layer_norm_fp8`×80；`fp16_nvjet` 500→100 |

**One-liner:** EncFp8 = `vl_self_attention` 4×BasicTransformerBlock 静态 FP8（QKV/to_out/FFN）+ 现成 DiT glue（QKV-shared / gelu_fp8 / attn-out / FFN_LN_FP8）。encode 墙钟 −1.39 打到盘点 −0.5～−2；e2e 仅 −0.4（噪声）；gate 过。**默认不合**，可升 GO 吃 encode 填缝。

**建议：** 不合基线；可 backlog / 升 GO。**不要**自批下一刀。state_encoder CategorySpecificMLP 未动（非标准 Linear）；与 LlmRmsQ 正交可叠。

---

## What changed

| path | change |
|---|---|
| `mlc-vla/.../quantization/fp8.py` | preset `e4m3_gr00t_enc`（24）+ `e4m3_gr00t_llm_l3_enc`（88=L3+24）；**不**走 `_GR00T_BB_SHARED_EXCLUDE` 对 `vl_self_attention` 的全排除 |
| scales | `fp8_scales_enc_vlsa.npz`（48）+ merge `fp8_scales_llm_l3_enc.npz`（176）；real_features_demo×8；QKV 共享 input_scale |
| pack | `gr00t_n17_bb_fp8_l3_enc_i4_unirt` |
| glue | **无新 glue** — VL-SA 复用 `BasicTransformerBlock` 已有 FP8 路径 |
| **未动** | DiT；Vision；LLM QKV/RMS；state_encoder；vlln；降步 |

Compile：`--fp8 e4m3_gr00t_llm_l3_enc --fp8-gemm`；functions `embed_vision,backbone_llm,encode_condition`；88 静态 FP8。

---

## Timing（lockfreq；gpc=1575 / nvd=1692；GATE PASS）

Same-session：bb L3 vs L3+EncFp8；DiT = `..._take_fuse_adastatic_unirt`。warmup=8 iters=40。

| stage | L3+AdaStatic ref | **L3+EncFp8** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.080 | 19.103 | +0.022 |
| backbone_llm | 19.817 | 19.999 | +0.182 |
| **encode_condition** | **6.525** | **5.137** | **−1.388** |
| denoise_step | 16.253 | 16.022 | −0.231 |
| denoise_loop | 50.410 | 49.612 | −0.798 |
| e2e_head | 58.852 | 58.577 | −0.275 |
| **e2e_full** | **98.656** | **98.249** | **−0.407** |

相对锁基线 ~99.35：本 session ref 抖到 98.66。**权威：encode −1.39 / e2e −0.41（同 session）**。  
盘点估 Δe2e −0.5～−2 → e2e 贴下沿；encode 落在桶内。距 66.7 仍 ~31+ ms。

> denoise_loop −0.80 / llm +0.18：DiT/LLM 包未改 EncFp8，记为会话噪声；刀收益以 **encode_condition** 为准。

---

## Accuracy（dual-track）

UniRT FP16 bb vs L3+EncFp8 bb → shared AdaStatic denoise_loop。**Relative**（非 PT）。

| metric | value | Hill |
|---|---:|:---:|
| overall cos | 0.999979 | >0.999 |
| overall mse | 5.034e-05 | <5e-4 |
| overall mean_abs | 3.852e-03 | — |
| **overall pass** | **True** | **PASS** |
| isolate overall cos/mse | 0.999993 / 1.67e-5 | PASS |
| per-dim | 119/132（iso 124/132） | report |
| encode_vl isolate cos | 0.9988 | soft feature |
| backbone_llm cos (fp16 vs cand=L3) | 0.835 | L3 相对（Enc 未动 LLM） |
| embed_vision cos | 1.0000 | — |

---

## nsys A/B（encode_condition，~20 iter 含 warmup）

| bucket | L3 ms | L3 inst | **EncFp8 ms** | **inst** | Δ |
|---|---:|---:|---:|---:|---|
| **fp16_nvjet** | **57.3** | **500** | **1.47** | **100** | **−55.8**（VL-SA Linear 迁走） |
| **fp8_gemm** | 0 | 0 | **28.0** | **480** | **+HIT** |
| **gelu_fp8** | 0 | 0 | **2.99** | **80** | **+HIT** |
| **layer_norm_fp8** | 0 | 0 | **1.37** | **80** | **+HIT** |
| quantize | 0 | 0 | 1.30 | 160 | 小税（attn-out 等） |
| softmax | 16.9 | 80 | 16.8 | 80 | ~0 |
| **listed total** | **126.4** | — | **92.0** | — | **−34.5 ≈ −1.7/iter** |

Causal: VL-SA nvjet → FP8 cutlass；入口/出口税换 `layer_norm_fp8` + `gelu_fp8`；净利与墙钟 encode −1.39 同量级。

---

## Artifacts

- Pack: `/work/gr00t_fp8_phase_a/gr00t_n17_bb_fp8_l3_enc_i4_unirt`
- Bench: `/work/gr00t_fp8_phase_a/encfp8_scout/`（stages / gate / nsys / measure_summary）
- Shared: `gr00t-encfp8-scout.md`, `encfp8_measure_summary.json`, `encfp8_nsys_ab_summary.json`, stages/gate json
- Source patch（no commit）: apex_rt `fp8.py`（`.bak_pre_encfp8`）— presets only

---

## Ask / 不自批

1. Soft-GO 维持默认不合，还是升 GO 合入吃 encode −1.4？
2. 若合：是否与已批 **LlmRmsQ** 叠包（L3+QKV-rmsq+Enc）再锁新基线？
3. state_encoder / vlln 是否另开薄刀（CategorySpecific 非标准 Linear，收益预期更矮）？
4. 下一刀仍不自批。
