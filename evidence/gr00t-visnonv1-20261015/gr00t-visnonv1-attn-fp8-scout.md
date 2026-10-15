# GR00T VisNonV1 — ViT attn FP8 + shared Q scout

- Date: 2026-10-15 Asia/Shanghai (~10:15)
- Status: **wired + compiled + lockfreq staged + nsys A/B**; **speed FAIL**; overall gate PASS; **默认不合**
- Hill gate: overall **cos>0.999 AND mse<0.0005** (per-dim report-only)
- Steering: quant / fusion / ops / precompute only — **no** 2-step; **禁止重放 V1 plain MLP**
- Thor: `pi05-forge-agent` / thor-2239; work `/work/gr00t_fp8_phase_a/`
- Baseline stack: **L1+L3+D1+crosskv+D1take+AdaStatic** (e2e_full ~99.35; same-session ref ~99.64)

---

## Verdict

| | |
|---|---|
| **Go / no-go** | **NO-GO**（默认不合） |
| Speed | **FAIL** — embed_vision **+1.37 ms**；e2e_full **+1.48 ms** |
| overall gate | **PASS** cos 0.999966 / mse 8.13e-5 |
| embed feature cos | **~0.9906** soft（vs FP16 / vs L3 同级；相对 gate 弱信号） |
| nsys | **HIT** shared-Q 路径；`quantize_fp8` 税 ~0.57 ms/iter 吃掉 FP8 GEMM 收益 |

**One-liner:** VisNonV1 把 ViT `attn.qkv/proj` 换成 FP8 + 一次 shared Q（禁 MLP），精度 overall 过，但 **quantize_fp8 税 + FP8 cutlass 打不过基线 fused-f16 nvjet**，embed/e2e 双回归；与 V1 plain 同病不同灶。后续若挖，应走 π0 `res_ln_fp8` / `vit_fp8_o_half_in` 清税，而不是再加 plain Linear。

---

## What changed

| path | change |
|---|---|
| `mlc-vla/.../modules_vit.py` | `VisionAttention._qkv_maybe_prequant` / `_proj_maybe_prequant`；env `MLC_VLA_GR00T_VIT_ATTN_SHARED_FP8` / `VIT_ATTN_O_FP8`（默认开） |
| `mlc-vla/.../fp8.py` | presets `e4m3_gr00t_vit_attn`（48）、`e4m3_gr00t_llm_l3_vit_attn`（112 = L3 64 + attn 48） |
| calib | `calib_vit_attn_standalone.py` → `fp8_scales_vit_attn.npz`；merge → `fp8_scales_l3_vit_attn.npz` |
| pack | `gr00t_n17_bb_fp8_l3_vit_attn_i4_unirt` |
| **未动** | ViT MLP（`VIT_GELU_FP8=0` / `VIT_FC1_GELU_Q_EPI=0`）；DiT AdaStatic 基线包 |

Compile：`--fp8 e4m3_gr00t_llm_l3_vit_attn --fp8-gemm`；functions `embed_vision,backbone_llm,encode_condition`。

---

## Timing（lockfreq；gpc=1575 / nvd=1692；GATE PASS）

Same-session：bb L3 vs VisNonV1；DiT = `..._take_fuse_adastatic_unirt`。

| stage | L3+AdaStatic ref | **VisNonV1** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.519 | **20.894** | **+1.374** |
| backbone_llm | 19.874 | 20.395 | +0.521 |
| encode_condition | 6.504 | 6.694 | +0.189 |
| denoise_step | 15.962 | 16.090 | +0.128 |
| denoise_loop | 50.107 | 50.242 | +0.135 |
| e2e_head | 60.538 | 60.268 | −0.270 |
| **e2e_full** | **99.639** | **101.124** | **+1.485** |

相对锁基线 ~99.35：本 session ref 略抖到 99.64；**候选相对同 session ref 回归**，非测量噪声可吞。

目标估 −2～−5 → **未达成**（符号相反）。

---

## Accuracy

Method: UniRT FP16 bb vs VisNonV1 bb → shared AdaStatic `denoise_loop`（相对 gate；非 PT）。  
Caveat：`backbone_llm` 输入随机，不链式 embed→LLM；**Vision 质量看 embed_vision feature cos**。

| | cos | mse | mean_abs | pass |
|---|---:|---:|---:|:---:|
| **overall（action）** | **0.999966** | **8.13e-5** | 4.24e-3 | **True** |
| embed_vision vs FP16 | 0.990569 | 3.51e-3 | 3.36e-2 | — |
| embed_vision vs L3 | 0.990569 | 3.51e-3 | 3.36e-2 | — |
| embed L3 vs FP16 | ~1.0（L3 不碰 Vision） | — | — | — |
| backbone_llm vs FP16 | （见 JSON；L3 路径） | | | |

Per-dim：`119/132` pass（报告-only）。

---

## nsys A/B（embed_vision；12 profiled iters）

| | L3（FP16 ViT attn） | VisNonV1（attn FP8） |
|---|---|---|
| Attn/MLP GEMM | **nvjet f16 bias fused** + cutlass f16 | 部分改 **cutlass GemmUniversal FP8**（576 inst） |
| Q 税 | 无 | **`quantize_fp8_fp16_kernel` 6.81 ms / 12 ≈ 0.57 ms/iter**（576 = 24×2×12 → shared-Q+proj 各一发） |
| flash attn | ~1.03 ms/iter | ~1.03 ms/iter（未动） |
| Diagnosis | FP16 attn 走 fused bias GEMM | FP8 路径 **拆出独立 Q**；FP8 GEMM 收益盖不住 Q 税 + 丢 nvjet fusion → embed **+1.37** |

Artifacts: `visnonv1_attn_fp8_scout/nsys/{l3,visnonv1}_embed.nsys-rep` + `nsys_ab_summary.json`。

---

## Blockers / next

1. **NO-GO 合入** — 速度符号错误；勿叠进 ~99.35 基线。
2. 若再开 Vision 非 V1：优先 π0 **`vit_fp8_res_ln` / LN→e4m3 融进 Q** 与 **`vit_fp8_o_half_in`（BiasFromHalf）**，目标是 **杀掉 `quantize_fp8` launch**（本刀已证明 shared-Q 接线正确，税仍在）。
3. 勿重放 V1/V1b MLP；本刀已遵守。
4. 特征 cos~0.99：若 dig 续开，补 real-act calib / 链式 gate。
5. 并行刀 **DitAttnE4** 不受本结论阻塞。

---

## Artifacts

- Pack: `/work/gr00t_fp8_phase_a/gr00t_n17_bb_fp8_l3_vit_attn_i4_unirt`
- Scales: `fp8_scales_vit_attn.npz`, `fp8_scales_l3_vit_attn.npz`
- Stages/gate/nsys: `visnonv1_attn_fp8_scout/`
- Report (shared): `/home/nio/shared/gr00t-fp8/gr00t-visnonv1-attn-fp8-scout.md`
- Code: Thor apex_rt `mlc-vla`（`modules_vit.py` / `quantization/fp8.py`）；backup `modules_vit.py.bak_pre_visnonv1`
