# GR00T DiT FP8 消 quantize 税 — AiInfraKB 可复用草稿

> 目标库：**AiInfraKB**（不是 agent-kit）。本文整理 2026-10-14 Thor/LT5 一轮可复用教训，供 KB ingest。

---

## 1. 标题建议

`推理：FP8Linear 入口 quantize 税与 fused e4m3-out 消税模式（GR00T DiT / synapsex）`

---

## 2. Problem

- UniRT/MLC 路径上 `FP8Linear.forward` 对 half 激活先发 **standalone `quantize_fp8`**，再 GEMM。
- GR00T full DiT 覆盖下，quantize 可占 denoise_step **~15%+** 墙钟；锁频 nsys 可见成百上千次 `quantize_fp8_fp16_kernel`。
- 与 π0.5 对比：对方用 `geglu_fp8` / `ada_rms_fp8` 把激活 Q **融进** norm/激活核，再 `forward_prequantized`，几乎无独立 Q 税。
- GR00T AdaLN 是 **LayerNorm+(1+scale)+shift**（不是 RMSNorm+gate），不能照搬 `ada_rms_fp8`。

---

## 3. Solution（模式）

### 3.1 通用公式

```
x_half → [fused_op → e4m3] → FP8Linear.forward_prequantized(x_q)
```

融核负责「计算 + 静态 per-tensor Q（/act_scale，clip ±448）」；Linear 跳过入口 quantize。

### 3.2 本轮落地的三个算子

| 算子 | 公式 | so / 符号 | 图侧 |
|---|---|---|---|
| `gelu_fp8` | e4m3(gelu_tanh(x)/s) | `libsynapsex_gelu_fp8.so` / `synapsex_gelu_fp8` | `flashrt.gelu_fp8` |
| `layer_norm_fp8` | e4m3(LN(x;γ,β)/s) | 本地 `.cuh`（可后上收） | `flashrt.layer_norm_fp8` |
| `ada_ln_fp8` | e4m3(LN_affine_free(x)*(1+scale)+shift)/s | `libsynapsex_ada_ln_fp8.so` / `synapsex_ada_ln_fp8` | `flashrt.ada_ln_fp8` |

### 3.3 synapsex 边界（硬规则）

- **只**放通用核；**禁止** `gr00t` / `dit` 模型名、temb MLP、DiT block 调度。
- C ABI + 独立 so；**不**链 libtvm；`GPU_ARCH=110/120`。
- mlc-vla：`dlopen` 优先 so（`MLC_VLA_*_SO` / `SYNAPSEX_HOME`），失败回落本地 `.cuh`。

### 3.4 图侧接线要点（mlc-vla）

- Env 门（默认开）：`MLC_VLA_GR00T_FFN_GELU_FP8`、`ATTN_OUT_FP8`、`QKV_SHARED_FP8`、`FFN_LN_FP8`、`ADA_LN_FP8`。
- `ADA_LN_FP8` 启用时：**跳过** 对该 `x_q` 的 B3 shared `quantize_fp8`；cross **encoder K/V** 仍走 shared Q。
- AdaLN：`modulation(temb)` 仍在 Python；核只吃 scale/shift。

---

## 4. Evidence / 数字指针

| 项 | 位置 |
|---|---|
| 设计 | `gr00t-ada-ln-fp8-design.md` |
| 计划 / 税分析 | `gr00t-fp8-quantize-tax-plan.md` |
| 状态 | `gr00t-fp8-status.md` |
| **双交付基线快照** | `gr00t-fp8-baseline-snapshot.md` |
| 精度表 | `gr00t-fp8-accuracy-report.md`；`fp8_*_gate_with_mabs.json` |
| 精度图 | `gr00t-dit-fp8-precision-map.png` |
| Thor 速度 | `expand_bench/full_dit_phase_*_speed_report.json`；`baseline_snapshot_ada_ln/stages_*.json` |

### 关键里程碑（Thor 锁频）

| 阶段 | quantize% / ms | denoise_loop× | e2e_full× | 精度 dims0–31 |
|---|---|---|---|---|
| full_dit 无融合 | ~15%+ | ~1.18 | — | ~25/32 |
| Phase A (gelu+to_out) | ~12% | ~1.17 | — | — |
| +B3 QKV shared | ~3% | ~1.28 | — | — |
| +LN_FP8 | **2.2% / 0.30** | ~1.27 | — | 26/32 |
| +ada_ln_fp8 | **1.64% / 0.225** | **1.26** | **1.13** | **26/32** |
| qkv24（精度轨） | — | ~1.0 | — | **32/32** |

---

## 5. Don'ts / 坑

1. **`MLC_VLA_FLASHRT_ROOT`**：Thor 容器 `/srcs/FlashRT` 可能空挂载；必须 `/srcs/data/FlashRT`，否则 `flashrt.available()==False` 静默掉 Phase A。
2. **不要**把 float8 权重在 loader 里 `astype` 成 e4m3 却无 scale — 会跳过 `materialize_fp8_weights` 的正确 Q，runtime alpha 双重 scale。
3. **不要**把 AdaLN 当成 `ada_rms`；公式不同，需独立 `ada_ln_fp8`。
4. **不要**用 denoise-only 升「全链路基线」— Hill standing rule：必须 stages+e2e **且** overall+per-dim cos/mse/mean_abs。
5. **速度轨 ≠ 精度轨**：full_dit/ada_ln ~26/32；交付精度仍看 qkv24 32/32，除非另开 scale/覆盖精度刀。
6. **synapsex 不写 DiT glue**；模型调度留 mlc-vla。
7. Push **只**公司 GitLab（`ad-gitlab.nioint.com`），永不 GitHub（本轮个人 mirror remote）。

---

## 6. Hybrid e2e 测法（可复用）

DiT-only FP8 包无 ViT/LLM 时：

```
pack_bb  = FP16 vit_llm_flash_unirt   # embed_vision, backbone_llm, encode_condition
pack_dit = FP16 temb_fix | FP8 ada_ln  # denoise_step/loop
e2e_full = vision → llm → encode → denoise_loop   # 双 Executor，墙钟+sync
```

脚本参考：Thor `/work/gr00t_fp8_phase_a/bench_hybrid_stages_ada_ln.py` + `run_baseline_snapshot_ada_ln.sh`；锁频 `thor_bench_gate.sh`。

---

## 7. 代码锚点（公司 GitLab）

| 仓 | 分支 | 提交 |
|---|---|---|
| synapsex | `feat/gelu-fp8-op` | `0cd45c0` gelu |
| synapsex | `feat/ada-ln-fp8` | `1ff9653` ada_ln |
| mlc-vla | `feat/gelu-fp8-synapsex` | `2dd3cf0` Phase A/B/LN/ada_ln wiring |

远程：`ad-gitlab.nioint.com:ad/project_r_system/ai_infer/{synapsex,mlc-vla}`。

---

## 8. KB tags（建议）

`fp8` `quantize-tax` `forward_prequantized` `synapsex` `mlc-vla` `gr00t` `dit` `thor` `e2e-bench` `accuracy-gate`
