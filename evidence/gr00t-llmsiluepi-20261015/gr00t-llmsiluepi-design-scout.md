# GR00T LlmSiluEpi — 设计 scout（只估 Δ + 有无核）

- Date: 2026-10-15 ~11:25 Asia/Shanghai
- Status: **设计-only**；**未改代码 / 未编 cand pack / 未合入 / 未重放 L2/V1/VisNonV1/AttnScore/DitAttnE4/DitSoftAdd 挖核**
- Baseline stack: **L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4**
- e2e_full **~90.3**（Cg4 same-session **90.295**；`CURRENT_BASELINE.md`）
- 距 66.7 **~23.6 ms**
- bb pack: `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_i4_unirt`（alias `..._baseline_L1L3LlmRmsQ_unirt`）
- Thor/LT5: 复用 L3 / LlmRmsQ backbone_llm nsys（EncFp8/Cg4 **不改** LLM MLP；无需补捕）
- FLASHRT_ROOT 参考：LT5 `/home/nio/codes/ai_infra/r-infra/FlashRT`（= Thor `/srcs/data/FlashRT` 同源）

---

## Verdict: **Soft-GO（可 glue FlashRT，不挖新核；默认不合）**

| | |
|---|---|
| **有无现成核** | **有** FlashRT 元算子 `silu_mul_split_fp8_fp16`（真 SiLU×up→e4m3）；**无** synapsex/`mlc-vla` BYOC 封装；**无** SM100 CUTLASS **Silu** GEMM epi（仅有 GeGLU/GELU） |
| 估 Δ **backbone_llm** | **−0.3～−1.0 ms**（保守）；乐观 −1.0～−1.5（带宽/launch 多吃一点） |
| 估 Δ **e2e_full** | **−0.3～−1.0 ms**（bb-only；≈ llm） |
| vs inventory v4 −1～−3 | **偏乐观** → 本 scout **下修**（L1 后 silu×mul **已融**，只剩 down 入口 Q） |
| 风险 | 低～中（glue）；精度非 bit-identical（静态 Q 进 silu 核） |
| 默认 | **不合**；记 backlog；**勿当填缝主刀**；确认架构师升 GO 再 wire |
| **禁止本轮** | 挖 SM100 SiluMulE4m3 新核；merge gate_up；编 pack |

**一句话：** 现成核在 FlashRT（groot eager 已用）；UniRT 缺的是 `gelu_fp8` 同款 shim+`Qwen3MLP` glue。GEMM-epi 级 Silu→e4m3 **仍核债**（π0 是 GeGLU）。ROI 修订后薄，**Soft-GO / 默认不合**。

---

## 1. 当前图与 nsys 归因（复用 L3 / LlmRmsQ）

### 图（L1+L3+LlmRmsQ 后，`modules_llm.Qwen3MLP`）

```text
x → (post-LN → Q) → gate_proj FP8 GEMM → fp16
                  ↘ up_proj   FP8 GEMM → fp16
        h = silu(gate)*up     ← TVM fused_silu_multiply5  (已融，fp16)
        h_q = quantize_fp8(h, down.input_scale)   ← 独立 launch
        y = down.forward_prequantized(h_q)        ← FP8 GEMM
```

代码债注释已写明：「无现成 Silu→e4m3 fused epi（异于 V1b BiasGeluE4m3），本刀只消 down 入口 Q 税。」

### nsys（backbone_llm）

| 来源 | bucket / 核 | 总量 | ≈/iter | 备注 |
|---|---|---:|---:|---|
| L3 A/B（12 it） | **`fused_silu_multiply5_kernel`** | 22.433 ms / L192 | **~1.87 ms** | 16 层 ×12；**silu×mul 已一核** |
| L3 A/B | quantize 总桶 | 19.466 / L768 | ~1.62 | gate/up + o/down |
| L1→L3 Δ quantize | o+down 增量 | +4.92 / +384 | **~0.41**（二者合计） | down 单路 **~0.20～0.25** |
| LlmRmsQ（~16 it） | `quantize_fp8_fp16_kernel` | 7.016 / L512 | **~0.44** | **o+down** 的 flashrt Q（A2 路径）→ down **~0.22** |
| LlmRmsQ | `quantize_kernel` | 18.35 / L512 | ~1.15 | 多半 gate/up 入口（非本刀） |
| L3 | FP8 cutlass（含 GU+down+…） | 68.5 / L768 | ~5.7 | 相邻 GEMM；**本刀不改 GEMM** |
| — | 独立 `silu` / 独立 `mul` | **0** | — | 已被 TVM fuse |

**本刀可动税（保守）：** down 入口独立 Q **~0.20～0.45 ms/iter** + silu 出 fp16 再读入 Q 的带宽/launch。  
**不可再算：** 「把 silu 和 mul 融起来」——已经融了。

EncFp8 / Cg4 不碰 LLM MLP → **不必补捕**；上表对当前 ~90.3 基线仍成立。

---

## 2. 有无现成核？候选 API 与缺口

### ✅ 可复用（FlashRT，真 SiLU）

| API | 位置 | 语义 | GR00T 匹配 |
|---|---|---|---|
| **`silu_mul_split_fp8_fp16(gate, up, out_e4m3, n, d_scale)`** | `FlashRT/csrc/kernels/activation.cu` + `bindings.cpp` | `e4m3(silu(gate)*up/scale)`；**分刀** gate/up | ✅ 与 `gate_proj`/`up_proj` 分 Linear **同构** |
| `lingbot_silu_mul_fp8_mpad_*` / merged | `lingbot_silu_mul_fp8.cu` | 同式 + M-pad / merged | 可用但带 pad/bf16；非首选 |
| eager 范例 | `FlashRT/.../groot_n17/pipeline_thor.py` | 已 `fvk.silu_mul_split_fp8_fp16` → down FP8 | ✅ 同模型族 |

### ⚠️ 名字像但不适用（GELU / 别模型）

| API | 问题 |
|---|---|
| `flashrt.geglu` / `geglu_fp8` / `gate_silu_mul_merged_*` | **历史误称**：实为 **tanh-GELU**，不是 SiLU；π0 Gemma 用 |
| `synapsex/gelu_fp8` | `gelu_tanh(half)→e4m3`；无 mul、非 SiLU |
| `fp8_geglu_epi_sm100` / `fp8_gu_geglu` / BiasGeluE4m3 | **GeGLU/GELU** GEMM epi；要 **merged gate_up** + 改激活 |
| `grouped_swiglu` | MoE 分组 cublas；非本 LLM dense SwiGLU |
| FP4 `silu_mul_*_nvfp4` / qwen block128 | 输出 FP4 / 别 shape；非 e4m3 per-tensor down |

### ❌ 缺口（UniRT / synapsex / BYOC）

| 缺口 | 说明 |
|---|---|
| mlc-vla `flashrt.silu_mul_fp8`（或同名） | **无**；仅有 `geglu_fp8` / `gelu_fp8` / `quantize_fp8` |
| synapsex `silu_mul_fp8` so | **无**（有 `gelu_fp8` 可作 fork 模板） |
| SM100 **SiluMulE4m3** CUTLASS epi | **无**（仅 GeGLU compact / BiasGeluE4m3） |
| Relax pattern 匹配 split silu×up→e4m3 | **无**现成；需 shim DPS 或 synapsex 封装 |

### 推荐落地路径（若升 GO；本 scout **不 wire**）

1. **Glue-first（推荐）：** 仿 `gelu_fp8`：shim 调 FlashRT `silu_mul_split_fp8_fp16`（或 synapsex 薄封装同式）→ `Qwen3MLP.forward` 在 DOWN_FP8 时走  
   `h_q = silu_mul_fp8(gate, up, down.input_scale)` → `down.forward_prequantized(h_q)`，**删** `fused_silu_multiply` + 独立 `quantize_fp8`。  
   Effort：**S**（~0.5 d glue+compile+nsys）；**无需新 CUDA 算法**。
2. **不推荐本轮：** merge `gate_up` + 新 Silu GEMM epi（π0 GeGLU epi 换激活）→ **新核债**，ROI 才可能靠近旧估 −1～−3。

---

## 3. 估 Δ（保守区间）

| 杠杆 | 估节省 | 依据 |
|---|---:|---|
| 消 down 入口 `quantize_fp8` | **−0.20～−0.45** | LlmRmsQ flashrt Q 半额；L1→L3 o/down 增量半额 |
| 一趟写 e4m3，少写/读 fp16 `h` | **−0.1～−0.5** | 带宽；与 silu 核合并后不确定 |
| launch −16/iter | **~0～−0.1** | Thor 上常被淹没 |
| **合计 Δ llm / e2e_full** | **−0.3～−1.0** | **保守报告带** |
| 乐观上沿 | **−1.0～−1.5** | 若 silu_mul_fp8 不慢于 fused_silu 且 Q 全吃 |
| GEMM-epi 级（需新核） | **−1～−3?** | **本轮不做**；仍核债 |

相对 ~90.3：落地后约 **89.3～90.0**；距 66.7 仍 **~22.6+ ms**。  
**冲不满 15Hz**；只是 bb 尾税小刀。

---

## 4. 风险 / 非目标

| 风险 | 缓解 |
|---|---|
| 误接 `geglu_fp8`（GELU） | 硬用 `silu_mul_split_*`；nsys/单测对 SiLU 公式 |
| feature cos 再软 | overall 门控照旧；报告 feature |
| 当主刀填 23 ms gap | **否** — Soft backlog |
| 重开 L2/V1/… | **禁**（任务约束） |

---

## 5. Ask 架构师

1. Soft-GO 维持默认不合，还是升 **GO glue**（FlashRT `silu_mul_split_fp8`，不挖 epi）？
2. 若 glue：封装落 **mlc-vla shim 直调 FlashRT**，还是先 **synapsex `silu_mul_fp8` so**（对齐 gelu_fp8 边界）？
3. GEMM-epi Silu 是否单开核债 epic（本 scout **NO**）？

---

## 6. Artifacts

- 本报告: `/home/nio/shared/gr00t-fp8/gr00t-llmsiluepi-design-scout.md`
- nsys 复用: `l3_nsys_ab_summary.json`, `llmrmsq_nsys_ab_summary.json`
- 图: `r-infra/mlc-vla/.../gr00t_n17/modules_llm.py` `Qwen3MLP`
- 核: `FlashRT/csrc/kernels/activation.cu` `silu_mul_split_fp8_*`；范例 `groot_n17/pipeline_thor.py`
- 基线: `CURRENT_BASELINE.md` / `gr00t-cg4-merge.md`（e2e **90.295**）
