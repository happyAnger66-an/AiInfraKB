# GR00T DitAttnE4 scout — DiT attn 出口 → e4m3（清 A2 `to_out` quantize 税）

- Date: 2026-10-15 ~10:05 Asia/Shanghai
- Status: **定位 + 估 Δ only**；**未改代码 / 未编 pack / 未跑 stages·overall**；**不合基线**
- Baseline: **L1+L3+D1+crosskv+D1take+AdaStatic** → e2e_full **99.347**（`CURRENT_BASELINE.md`）
- 验收口径（gr00t-optimize-gate）：e2e_full；overall cos>0.999 ∧ mse<0.0005；**禁 2-step**；禁重放 AttnScore f16 logits
- Thor / nsys 源：`dr_crosskv_bench` + `d1_take_nsys_ab`（quantize 桶在 D1take 后仍 ~0.41）；AdaStatic 合入后未重捕 nsys（外推同量级）
- 边界：接线 mlc-vla；**新核 → FlashRT/synapsex**；与 VisNonV1 **不抢** `modules_vit.py`（本刀只动 DiT attn 出口 / layout+Q）
- 对照：`gr00t-ditres-scout.md`（quantize=to_out 税）、`gr00t-attn-score-scout.md` / `gr00t-attn-score-cross-f16.md`（**f16 logits NO-GO，勿重做**）、π0 F2b `_draft_f2b_attn_fp8out.md`

---

## Verdict: **SOFT-GO（可设计新核测，默认不合）**

| | |
|---|---|
| 估 Δe2e_full（修订） | **−0.2～−0.6 ms**（inventory −0.5～−2 **偏乐观**；cast 税不在本刀） |
| GPU 天花板 | residual **`quantize_fp8` ~0.41 ms/loop（L≈144）**；其中 **≤128L ≈ A2 to_out** |
| 可测性今日 | **否**（无现成「attn 直出 e4m3」核；纯胶水无法跳过 scaled Q） |
| 风险 | 中：需 **fused layout→e4m3** 新核；精度非 bit-identical；π0 F2b 示警「Q 融进重 epi 会亏」 |
| 默认 | **不合**；让路 VisNonV1；本刀 backlog / 填缝 |

**一句话：** A2 已把 `to_out` 接到 FP8 GEMM，剩下的就是独立 `quantize_fp8` 薄税。清它必须让 attn 出口（BTD）**带 scale 直出 e4m3**；GR00T DiT 是 matmul 路径，**不能**搬 π0 `varlen_attn_fp8out`；也**不是** AttnScore（f16 QK）。ROI 修订后偏薄，值得记一刀设计，不当主刀。

---

## 1. 定位（代码 + nsys）

### 1.1 今日路径（已是 A2，税仍在）

`modules_dit.py` `BasicTransformerBlock._to_out_maybe_prequant`（`MLC_VLA_GR00T_ATTN_OUT_FP8` 默认 ON）：

```text
attn out (half BTD)
  → flashrt.quantize_fp8(out, to_out.input_scale)   ← 本刀要消的 launch
  → to_out.forward_prequantized(...)                 ← FP8 GEMM 已吃 e4m3
```

默认 `DIT_LAYOUT=0` 的 `_attention`：QK **f32** matmul → softmax → PV half → `permute+reshape` → 上式。  
`DIT_LAYOUT=1`：`dit_pack_out` **仍写 half**，再进同一 helper（DitLayout 已 NO-GO，勿重开整包 layout）。

### 1.2 nsys 钉名（D1+crosskv / D1take 仍同量级）

| 项 | 值 | 来源 |
|---|---|---|
| `quantize` 桶 | **0.412～0.415 ms/loop**，**L=144** | `nsys_baseline_parse` / `d1_take_nsys_ab` |
| 期望 to_out launches | 32 blocks × 4 steps = **128** | AlternateVLDiT |
| 余量 | **~16 L** TBD（不假定本刀清光 144） | — |
| 邻接 layout | `fused_transpose3_reshape13` **0.491 ms / 128L**（BNTH→BTD） | top15 |
| **不在本刀** | `fused_*_cast6`（Q→f32）、magma QK f32、softmax | AttnScore / SoftAdd 边界 |

DitRes 已判：清 0.41 的正道是 **attn→e4m3**，不是 `proj_out_2` FP8。本 scout 即该 ID。

### 1.3 与 AttnScore / π0 F2b 的边界（硬）

| ID | 动什么 | 本刀？ |
|---|---|---|
| **AttnScore** | QK 输入 f16，`out_dtype` 仍 f32 | ❌ **已 NO-GO**；勿重做 f16 logits |
| **π0 F2b** `varlen_attn_fp8out` | FlashAttention epi 直写 e4m3 | ❌ GR00T DiT **无** varlen FA；且 F2b 实测 denoise **+5 ms**（外置 Q 更便宜） |
| **DitAttnE4** | 出口 BTD **scaled → e4m3**，跳过独立 `quantize_fp8` | ✅ |

---

## 2. 可行施工路径（设计草稿，本轮不做）

### 推荐：**P1 — fused transpose/reshape → e4m3**（轻 layout + Q）

1. FlashRT/synapsex 新核（名草案）`dit_pack_out_fp8` / `fused_bnth_to_btd_quantize`：  
   输入 PV half BNTH + `to_out.input_scale` → 输出 e4m3 BTD。  
2. `_attention`：PV 后走新核；`_to_out_maybe_prequant` 若 `out` 已 e4m3 → **直接** `forward_prequantized`（跳过 `quantize_fp8`）。  
3. 开关：`MLC_VLA_GR00T_ATTN_OUT_E4_FUSE=1`（默认 0 保基线）。  
4. **不要**把 Q 塞进 QK/softmax/PV 重 epi（π0 F2b 教训）。  
5. **不要**重开 `DIT_LAYOUT=1` 整包；仅增「出口 e4」变体。

### 不推荐 / 否决

| 方案 | 为何否 |
|---|---|
| 搬 `varlen_attn_fp8out` | 几何/栈不符；F2b 净亏 |
| `op.astype(..., e4m3)` 冒充 | **无** `input_scale`；数值错；仍可能单发 cast |
| AttnScore 顺带清 Q | 因果在 QK cast，不在 to_out |
| 只关 `ATTN_OUT_FP8` 当 A/B | 测的是「FP8 to_out vs half to_out」，**不是**「消 Q」 |

### 若日后 GO 测：交付清单

- 同会话 lockfreq：stages（e2e_full / head / loop）vs AdaStatic 基线  
- overall gate vs 同 pack 参考  
- nsys：`quantize` L 是否 **144→≤16**（理想 →0）；`fused_transpose3_reshape13` 是否被新核替换；**禁止**出现 AttnScore 式 magma→hgemm 作为本刀成功标准  

Effort：核 + shim + 接线 ~0.5–1 d；编 DiT pack + 测 ~同历史刀。

---

## 3. 估 Δ（修订 inventory）

| 杠杆 | 乐观 GPU | 现实 e2e | 备注 |
|---|---:|---:|---|
| 消 to_out 相关 quantize（≤128L ≈0.37） | ≤0.37 | **−0.2～−0.5** | 墙钟有重叠；16L 余量可能仍在 |
| 融进现有 reshape（省 144 launch，reshape 工时≈不变） | +0～0.1 额外 | **−0.2～−0.6** | 最佳现实带 |
| inventory「连带减 cast」 | — | **不计入** | cast6 属 QK，非 to_out |
| 误融进 FA/PV 重 epi | — | **≤0 / 负** | π0 F2b |
| **本刀合规合计** | | **−0.2～−0.6** | vs inventory −0.5～−2 |

相对 gap **~32.6 ms**：**可忽略填缝**。不挡 15Hz 叙事；不替代 VisNonV1 / 更大路径。

---

## 4. Go / no-go 表

| verdict | **SOFT-GO** |
|---|---|
| Why soft | 因果清楚（A2 税=独立 Q）；正道=轻 layout→e4m3；与 VisNonV1/AttnScore 正交 |
| Why 默认不合 | e2e 先验 &lt;1 ms；**无现成核**不可今日测；编包成本相对 ROI 偏高 |
| 何时升级 GO 测 | VisNonV1 告一段落仍要抠 denoise 小数，且有人写 fused out-e4 核；或 nsys 重捕后 quantize 桶意外变大 |
| Do **not** | 重放 AttnScore f16；搬 F2b flash fp8out；重开 DitLayout 整包；降步；动 Vision/LLM |

---

## 5. Artifacts / 指针

| | |
|---|---|
| **本报告** | `/home/nio/shared/gr00t-fp8/gr00t-ditattn-e4-scout.md` |
| 基线 | `CURRENT_BASELINE.md` / `gr00t-adastatic-merge.md` |
| DitRes（移交本 ID） | `gr00t-ditres-scout.md` |
| AttnScore NO-GO | `gr00t-attn-score-scout.md` / `gr00t-attn-score-cross-f16.md` |
| inventory | `gr00t-15hz-gap-inventory-v3.md` §DitAttnE4 |
| 代码 | `mlc-vla/.../modules_dit.py` `_to_out_maybe_prequant` / `_attention` |
| π0 反例 | `projects/pi05_optimize/notes/_draft_f2b_attn_fp8out.md` |
| nsys | `nsys_baseline_parse.json` quantize 0.412；`d1_take_nsys_ab.json` ~0.415 |

---

## 6. Ask（给架构师）

1. 接受修订估 **−0.2～−0.6** 与 **SOFT-GO 默认不合**？  
2. 若要升 GO 测：批 **P1 fused BTD-e4 核**（FlashRT），还是先 VisNonV1 出数再说？  
3. 144L 中 ~16L 余量是否值得单独 dig（本刀可不挡）？
