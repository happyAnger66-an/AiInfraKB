# GR00T LlmRmsQ — RMS→e4m3 共享进 QKV scout

- Date: 2026-10-15 Asia/Shanghai (~10:30)
- Status: **wired + compiled + lockfreq staged + nsys A/B**; overall gate **PASS**；**默认不合**
- Hill gate: overall **cos>0.999 AND mse<0.0005** (per-dim report-only)
- Steering: quant / fusion / ops / precompute only — **no** 2-step; **禁止重放 L2 plain QKV**
- Thor: `pi05-forge-agent` / thor-2239; work `/work/gr00t_fp8_phase_a/`
- Baseline stack: **L1+L3+D1+crosskv+D1take+AdaStatic** (锁 ~99.35; same-session L3 ref **99.940**)

---

## Verdict

| | |
|---|---|
| **Go / no-go** | **Soft-GO（默认不合）** |
| Speed | **WIN** — e2e_full **−2.024 ms**；backbone_llm **−1.638 ms**（达盘点估 −0.5～−2 天花板） |
| overall gate | **PASS** cos **0.999810** / mse **4.580e-4**（贴 5e-4 门） |
| backbone feature cos | **~0.766** soft（vs FP16；与 L2 ~0.78 同级） |
| nsys | **HIT** `rms_fp8_kernel`×256；QKV nvjet **768→0**；FP8 GEMM **1024→1792** |

**One-liner:** LlmRmsQ = `input_layernorm`→FlashRT `rms_fp8`→q/k/v `forward_prequantized`（Qwen `*w` 用 `w−1` 适配 Gemma 核）；**不是** L2 的 RMS FP16 + 独立 `quantize_fp8`。墙钟 −2.0 / llm −1.6，路径 nsys 钉死；gate 贴门 + feature 软 → **默认不合**，架构师可升 GO 吃这 −2 ms。

**建议：** 不合基线；可 backlog / 升 GO。**不要**自批下一刀。Silu→e4m3 epi（LlmTax b）仍核债，本刀未做。

---

## vs L2（一句话）

| | L2（已 NO-GO） | **LlmRmsQ（本刀）** |
|---|---|---|
| 边界 | RMS **FP16 出** → 独立 `quantize_fp8` → QKV FP8 | **`rms_fp8` 直出 e4m3** → QKV `forward_prequantized` |
| 基线叠 | L1（无 L3） | **L3 + QKV** |
| e2e Δ | **−0.75** | **−2.02** |
| nsys | quantize 不变/税吃光 | **`rms_fp8` HIT**；QKV nvjet 清零 |

---

## What changed

| path | change |
|---|---|
| `mlc-vla/.../modules_llm.py` | `Qwen3DecoderLayer._rms_fp8_qkv` + `Attention.forward_prequant_qkv`；env `MLC_VLA_GR00T_LLM_RMS_FP8`（默认开）。Qwen `*w` ↔ Gemma `(1+w)`：图上 `w_g=w−1` |
| `mlc-vla/.../fp8.py` | preset `e4m3_gr00t_llm_l3_qkv`（112 = L3 64 + QKV 48；`share_qkv_input_scale=True`） |
| scales | `fp8_scales_llm_l3_qkv.npz` = L3 + L2 QKV（224 keys；16/16 共享） |
| pack | `gr00t_n17_bb_fp8_l3_qkv_rmsq_i4_unirt` |
| **未动** | DiT AdaStatic；Vision；Silu epi；降步 |

Compile：`--fp8 e4m3_gr00t_llm_l3_qkv --fp8-gemm`；functions `embed_vision,backbone_llm,encode_condition`；112 静态 FP8；q/k/v scale 共享 16 组。

---

## Timing（lockfreq；gpc=1575 / nvd=1692；GATE PASS）

Same-session：bb L3 vs LlmRmsQ；DiT = `..._take_fuse_adastatic_unirt`。warmup=8 iters=40。

| stage | L3+AdaStatic ref | **LlmRmsQ** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.255 | 19.007 | −0.248 |
| **backbone_llm** | **20.166** | **18.528** | **−1.638** |
| encode_condition | 6.833 | 6.652 | −0.181 |
| denoise_step | 16.083 | 16.371 | +0.288 |
| denoise_loop | 50.168 | 50.925 | +0.757 |
| e2e_head | 59.863 | 59.941 | +0.078 |
| **e2e_full** | **99.940** | **97.916** | **−2.024** |

相对锁基线 ~99.35：本 session ref 略抖到 99.94；**候选相对同 session ref 实赚 −2.0**。  
目标估 −0.5～−2 → **打到上沿**。距 66.7 仍 ~31 ms。

> denoise_loop +0.76：DiT 包未改，记为会话噪声；权威以 e2e_full / backbone_llm 为准。

---

## Accuracy（dual-track）

UniRT FP16 bb vs LlmRmsQ bb → shared AdaStatic denoise_loop。**Relative**（非 PT）。

| metric | value | Hill |
|---|---:|:---:|
| overall cos | 0.999810 | >0.999 |
| overall mse | 4.580e-04 | <5e-4 |
| overall mean_abs | 8.194e-03 | — |
| **overall pass** | **True** | **PASS** |
| per-dim | 116/132 | report |
| backbone_llm cos (fp16 vs cand) | 0.7656 | soft |
| embed_vision cos | 1.0000 | — |

---

## nsys A/B（backbone_llm，~16 有效 iter 含 warmup）

| bucket | L3 ms | L3 inst | **LlmRmsQ ms** | **inst** | Δ |
|---|---:|---:|---:|---:|---:|
| **fp16_nvjet** | **29.1** | **768** | **0** | **0** | **−29.1**（QKV 迁走） |
| fp8_gemm | 85.6 | 1024 | 100.9 | 1792 | +15.3 / +768 |
| **rms_fp8** | 0 | 0 | **3.47** | **256** | **+HIT** |
| quantize (o/down 等) | 25.5 | 1024 | 25.4 | 1024 | ~0（QKV 入口不再走独立 Q） |
| subtract (w−1) | 0 | 0 | 0.47 | 256 | 小税 |
| **listed total** | **313.3** | — | **279.6** | — | **−33.7 ≈ −2.1/iter** |

Causal: QKV nvjet 清零进 FP8 cutlass；**入口税换成 `rms_fp8`（非 L2 `quantize_fp8`）**；净利与墙钟 llm −1.6 同量级。`w−1` subtract 仅 ~0.03 ms/iter，可后续用 Qwen-native `*w` 核或 fold-LN 消掉。

---

## Artifacts

- Pack: `/work/gr00t_fp8_phase_a/gr00t_n17_bb_fp8_l3_qkv_rmsq_i4_unirt`
- Bench: `/work/gr00t_fp8_phase_a/llmrmsq_scout/`（stages / gate / nsys / measure_summary）
- Shared: `gr00t-llmrmsq-scout.md`, `llmrmsq_measure_summary.json`, `llmrmsq_nsys_ab_summary.json`, stages/gate json
- Source patches（no commit）: apex_rt `fp8.py` / `modules_llm.py`（`.bak_pre_llmrmsq`）

---

## Ask / 不自批

1. Soft-GO 维持默认不合，还是升 GO 合入吃 −2 ms？
2. 若合：是否顺手消 `w−1`（Qwen `rms_fp8_mulw` 核 / fold weight into QKV）？
3. 下一刀仍不自批（LlmTax b Silu epi / EncFp8 / … 等架构师点名）。
