# GR00T B2 — Vision Soft glue+measure（`res_ln_fp8` + `o_half_in`）

- Date: 2026-10-15 Asia/Shanghai (~12:47)
- Status: **wired + compiled + lockfreq A/B + nsys A/B**；**速度 FAIL**；overall gate PASS（相对/非链式）；**embed feature 崩**；**默认不合入**
- Prior scout: `gr00t-vision-soft-scout.md`（Soft-GO 可迁 YES；估 Δembed −0.5～−1.5）
- Hill gate: overall **cos>0.999 AND mse<0.0005**；验收 **e2e_full**
- Steering: quant / fusion / ops / precompute only — **禁** VisNonV1 plain / V1 plain；**禁** 2-step
- Thor: `pi05-forge-agent` / thor-2239；`FLASHRT_ROOT=/srcs/data/FlashRT`
- Lock baseline stack: **L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi**（e2e ~89.8）

---

## Verdict

| | |
|---|---|
| **Go / no-go** | **NO-GO**（默认不合；建议不合） |
| Speed | **FAIL** — embed_vision **+0.370 ms**；e2e_full **+0.168 ms** |
| overall gate | **PASS** cos≈1.0 / mse=0（相对 gate；**不链式** embed→LLM→action） |
| embed feature cos | **0.418**（崩；Soft 数值不可用） |
| nsys | **res_ln_fp8 HIT**；**half_in PARTIAL MISS**（`kQuantizeHalfToE4m3` 仍在）；nvjet f16 大面积换成 cutlass FP8 |

**One-liner:** Soft glue 已接线且 `res_ln_fp8` 上图，但 **清税不完整**（仍有 `kQuantizeHalfToE4m3`）+ **丢掉 nvjet f16 fused GEMM**，墙钟 embed/e2e 双回退；更关键 **embed feature cos≈0.42** 说明数值路径/calib 未对齐。相对 overall PASS 不可当作 Vision 质量门。**不合入**。

---

## What changed（glue only；未合基线）

| path | change |
|---|---|
| `mlc-vla/.../modules_vit.py` | Soft：`VisionBlock.forward_fused` / `forward_from_prequant` / `_out_proj` half_in；禁 VisNonV1 路径于 Soft 编译 env |
| `mlc-vla/.../config.py` | `vit_fp8_res_ln` / `vit_fp8_o_half_in`（默认 False） |
| `mlc-vla/.../model.py` | 透传 Soft flags → `Qwen3VisionTower` |
| `mlc-vla/.../quantization/fp8.py` | preset `e4m3_gr00t_llm_l3_qkv_enc_vit_soft`（232 = 136+96） |
| scales | `fp8_scales_llm_l3_qkv_enc_vit_soft.npz`（lock Enc + vit_attn + vit_mlp 合并） |
| pack（新名字 only） | `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_vit_soft_i4_unirt` |
| **未动** | 锁 bb alias / DiT Cg4 / VisNonV1 env 默认行为（Soft 编译显式关） |

Compile：`--fp8 e4m3_gr00t_llm_l3_qkv_enc_vit_soft --fp8-gemm --set vit_fp8_res_ln=true --set vit_fp8_o_half_in=true`；env 禁 `VIT_ATTN_SHARED_FP8` / `VIT_ATTN_O_FP8` / `VIT_GELU_FP8` / V1b。

**未 commit**（等架构师批合 — 本刀建议 **不合**）。

---

## Timing（lockfreq；gpc=1575 / nvd=1692；GATE PASS）

Same-session：SiluMul lock bb vs Soft；DiT = Cg4。

| stage | SiluMul ref | **Soft** | Δ |
|---|---:|---:|---:|
| embed_vision | 18.886 | **19.256** | **+0.370** |
| backbone_llm | 17.169 | 17.341 | +0.172 |
| encode_condition | 5.192 | 5.162 | -0.030 |
| denoise_step | 14.016 | 13.738 | -0.278 |
| denoise_loop | 43.901 | 44.317 | +0.416 |
| e2e_head | 51.698 | 52.972 | +1.274 |
| **e2e_full** | **88.638** | **88.806** | **+0.168** |

相对 scout 估 −0.5～−1.5：**符号相反**（未达成）。

> denoise_* 抖动：DiT 未改，记会话噪声；刀收益以 **embed / e2e_full** 为准。

---

## Accuracy

Method: UniRT SiluMul bb vs Soft bb → shared Cg4 `denoise_loop`（相对 gate；非 PT）。  
Caveat：`backbone_llm` 输入随机，**不链式** embed→LLM→action；Vision 质量看 **embed feature cos**。

| | cos | mse | mean_abs | pass |
|---|---:|---:|---:|:---:|
| **overall（action）** | **1.000000** | **0.000e+00** | 0.0 | **True** |
| embed_vision feature | **0.417938** | 9.290e-01 | 7.513e-01 | — |
| backbone_llm | 1.0000000000000002 | 0.0 | | bit-identical（Soft 不碰 LLM） |
| per-dim | 132/132 | | | report |

embed feature **0.42** → Soft 出口不可用（calib 或 fused 数值错）；即使 overall PASS 也 **不得合入**。

---

## nsys A/B（embed_vision；12 profiled iters）

| 信号 | SiluMul ref (FP16 ViT) | Soft | 解读 |
|---|---|---|---|
| `res_ln_fp8` | 0 | **~3.715 ms/iter** | **HIT** |
| `layer_norm_fp8` | 0 | ~0.059 | 首层 HIT |
| `layer_norm*` | ~1.778 | ~0.101 | Soft 大部替换 |
| `kQuantizeHalfToE4m3` / Q | 0 | **~0.39 ms/iter** | **half_in PARTIAL MISS** |
| nvjet f16 bias | ~8.492 | ~0.649 | **LOST** |
| cutlass GEMM | ~4.464 | ~8.703 | FP8 Universal 顶上 |

Diagnosis: Soft 杀掉 VisNonV1 式 `quantize_fp8` launch，但 **BiasFromHalf 未吃满**（残留 `kQuantizeHalfToE4m3`），且 FP8 cutlass **打不过** 基线 nvjet f16 fused → 墙钟回退。数值侧 feature cos 崩，需另查 calib/残差图，不在本刀合入范围。

Artifacts: `vision_soft_measure/nsys/{ref,soft}_embed.nsys-rep` + `nsys_ab_summary.json`。

---

## Blockers / next

1. **NO-GO 合入** — 速度符号错 + feature cos 崩。
2. 若续挖 Soft：先修 **数值**（real-act calib 对齐 Soft LN→e4m3；核对 deepstack residual）；再修 **half_in BYOC 注册序/匹配**（清掉 `kQuantizeHalfToE4m3`）。
3. 勿回退 VisNonV1 plain / V1 plain。
4. 并行 **B1 DitSoftAdd** 不受本结论阻塞。
5. 代码已落 Thor apex_rt + LT5 工作树；**未 commit / 未改 CURRENT_BASELINE**。

---

## Artifacts

| | |
|---|---|
| Report | `/home/nio/shared/gr00t-fp8/gr00t-vision-soft-measure.md` |
| Pack | `/work/gr00t_fp8_phase_a/gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_vit_soft_i4_unirt` |
| Stages/gate/nsys | `/work/gr00t_fp8_phase_a/vision_soft_measure/` |
| Summary JSON | `vision_soft_measure_summary.json`（shared） |
| Scout | `gr00t-vision-soft-scout.md` |

## Ask 架构师

1. Soft **NO-GO** 认否？（建议认）
2. 续挖优先 **数值修复** 还是直接停 Soft、全力 B1？
3. LT5/Thor 工作树 Soft glue 保留作实验，还是 revert modules_vit？
