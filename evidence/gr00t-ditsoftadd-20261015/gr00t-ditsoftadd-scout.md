# GR00T DitSoftAdd scout — denoise attn softmax/cast 与 elem-add 再融 / 减 launch

- Date: 2026-10-15 ~11:10 Asia/Shanghai
- Status: **nsys 钉名（AdaStatic 新基线）+ PV 归因 + 设计草稿**；**未改代码 / 未编 pack / 未跑 stages·overall A/B**；**不合基线**
- Baseline: **L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic** → e2e_full **95.513**（`CURRENT_BASELINE.md` / EncFp8 merge）
- 验收口径（gr00t-optimize-gate）：e2e_full；overall cos>0.999 ∧ mse<0.0005；**禁 2-step**；禁重放 AttnScore / DitAttnE4 / DitLayout / L2 / V1 / VisNonV1
- Thor: `pi05-forge-agent` / thor-001；DiT `..._take_fuse_adastatic_unirt`；bb `..._l3_qkv_rmsq_enc_i4_unirt`
- nsys: `ditsoftadd_scout/nsys/adastatic_denoise_loop`（warm3/iters12，锁频 GATE PASS）；parse `nsys_baseline_parse.json`
- 边界：接线 mlc-vla；**新核 → FlashRT/synapsex**；与 Softmax 已融（cast）边界划清；**勿碰 QK dtype**

---

## Verdict: **SOFT-GO（可设计新核测，默认不合）**

| | |
|---|---|
| 估 Δe2e_full（修订） | **−0.2～−0.8 ms**（inventory −0.3～−1.0 **略偏乐观**） |
| GPU 天花板（本刀合规） | softmax 已融 **2.40** 难再抠；elem_add **2.27**（add2 **1.39** 主目标）；PV **0.79** 仅当 fused-attn 才动 |
| 可测性今日 | **否**（无现成 SoftAdd / residual+LayerNorm_fp8 核可 glue；纯 Relax 无法跨 PV+to_out 把 softmax 融进 residual） |
| 风险 | 中：需 **新核**（residual_add_layer_norm_fp8 或 to_out residual epi）；精度非 bit-identical 若动 epi |
| 默认 | **不合**；记设计 backlog；让路更大刀 / inventory v4 |

**一句话：** Softmax+cast **已经 fused**；它和 residual **add 中间隔着 PV + pack + to_out(+Q)**，不是相邻 launch。PV（wmma+nvjet_64×48）归因清楚 = probs@V，**不是** QK、也不是 DitRes。今日无廉价 wire；正道是 **attn residual → 下游 layer_norm_fp8 的 residual_add 融合**（或 to_out GEMM residual epi），ROI 修订后偏薄。

---

## 1. 新基线 nsys（AdaStatic 后补捕）

| 项 | 值 |
|---|---|
| GPU ms/loop | **46.645**（D1+crosskv 旧 ~48.5；AdaStatic 砍掉 bank nvjet ≈2.05，量级吻合） |
| `ada_bank_nvjet` (192×8) | **0**（已消） |
| take 残留 | **1.80** / L=48（D1take 已砍 ×256 bank take；剩 take3/4/…） |

### SoftAdd 焦点桶（ms/loop）

| bucket | ms | L | 核 |
|---|---:|---:|---|
| **attn_softmax** | **2.401** | 128 | `fused_softmax_cast5` 1.26 / L64 + `fused_softmax1_cast7` 1.14 / L64 |
| **elem_add** | **2.271** | 320 | **add2 1.386 / L64** + add3 0.885 / L256 |
| **attn_pv** | **0.787** | ~140 | wmma f16 0.397/L64 + nvjet_64×48 0.316/L64 + 边角 |
| attn_qk_f32 | 2.644 | 128 | magma — **禁动**（AttnScore NO-GO） |
| quantize | 0.411 | 144 | to_out Q — **DitAttnE4** 边界，非本刀 |

对照 D1+crosskv / D1take：softmax / add2 / add3 / PV **几乎不动**（±噪声）；外推成立，本发 nsys 只是钉死 AdaStatic 后仍在。

### PV 归因（清楚后再动）

| 证据 | 结论 |
|---|---|
| AttnScore cross-f16 后 wmma/nvjet_64×48 **仍 64L** | **不是 QK** |
| DitRes 已排除 `proj_out_2` | **不是** 残留 Linear |
| 位置：softmax(cast) → `matmul(probs,v)` | **= attn PV（probs@V）** |
| SoftAdd 可否吞 | 仅当做 **softmax↔PV fused attn**（近 FA / 新核）；**不**算进 residual-add 子刀 |

---

## 2. 图上为什么「softmax 再融 add」今天做不到

默认路径（`DIT_LAYOUT=0`，`modules_dit._attention` + `BasicTransformerBlock.forward`）：

```text
QK f32 matmul          ← 禁动
  → softmax + cast     ← 已 fused（2.40）
  → PV (probs@V)       ← 0.79
  → permute+reshape    ← layout
  → quantize? + to_out ← DitAttnE4 / FP8 GEMM
  → hidden += attn_out ← add2 (~1.39)   ★ SoftAdd 主目标
  → layer_norm_fp8     ← 0.71（FFN 入口）
  → FFN ...
  → hidden += ff_out   ← 多半落在 add3 族
```

- Softmax 与 add2 **不相邻** → 不能靠 TVM 再融一行 `op.add` 吃掉 softmax。
- Softmax 已带 cast → inventory「再融」= 融进 **PV epi** 或更重的 fused-attn，不是再写一个 soft+cast。

### add 归因（工作假设）

| 核 | ms | L/loop | 假设 |
|---|---:|---:|---|
| **add2** | 1.386 | 64 (=16×4) | **大 tensor residual**（attn 后主残差的一档 shape）；avg ~21 µs |
| **add3** | 0.885 | 256 | 小 elem-add 族（其余 residual / 碎片）；avg ~3.5 µs |

32 layers × 4 steps → softmax L=128 吻合；add2 仅 64 → 半档 shape（self/cross 分核）或仅一侧 residual 落独立 launch。精确 IR 映射未做（本轮不挖 TVM 图）；**不影响**「add2 是 SoftAdd 第一刀」的排序。

---

## 3. 设计草稿（本轮不实施）

### P0 推荐：**residual_add_layer_norm_fp8**（attn 残差 ⊕ FFN LN→e4m3）

1. FlashRT/synapsex 新核：`y = LN(residual + attn_out) → e4m3`（对照现有 `residual_add_rms_norm_fp8_*`，**DiT 是 LayerNorm 非 RMS**，不能直接搬）。
2. `BasicTransformerBlock.forward`：`hidden += attn_out` + `layer_norm_fp8` → 单发；开关 `MLC_VLA_GR00T_DIT_SOFTADD=1`（默认 0）。
3. 期望：消 **add2 ~1.39**（及对应 launch）；LN 时间大致保留 → GPU 净利 **≲1.0**；e2e **−0.3～−0.8**。
4. **不要**动 softmax/QK；**不要**重开 DitLayout。

### P1 备选：**to_out FP8 GEMM residual epi**

- `to_out` 已是 FP8 prequant GEMM；若 cutlass/nvjet 支持 C = AB + residual，可在 GEMM 出口吃掉 add2。
- 依赖栈与 calib；与 DitAttnE4（出口 e4m3）可能打架 → 二选一或排期。

### P2 不推荐当本刀

| 方案 | 为何否 |
|---|---|
| softmax 融进 PV（迷你 FA） | 新 attn 核；ROI 不确定；越界近 DitLayout |
| 搬 π0 `gated_res` / RMS residual | DiT 公式是 **LayerNorm + AdaLN**，不是 RMS gated |
| 重放 AttnScore f16 logits | **NO-GO** |
| 只改 Relax fuse add+cast | 无相邻 cast 可融；收益≈0 |

---

## 4. 估 Δ（修订 inventory）

| 杠杆 | 乐观 GPU | 现实 e2e | 备注 |
|---|---:|---:|---|
| add2 ⊕ layer_norm_fp8 | ≤1.4 | **−0.3～−0.8** | 主路径；需新核 |
| 再啃 add3 一部分 | ≤0.5 | **−0.1～−0.3** | 归因未钉死；次优先 |
| softmax 再融（无 PV） | ~0 | **~0** | 已 fused |
| 吞 PV 0.79 | 投机 | — | 另立 fused-attn ID，非 SoftAdd 填缝 |
| **本刀合规合计** | | **−0.2～−0.8** | vs inventory −0.3～−1.0 |

相对 gap ~28.8 ms：**填缝级**。不当主刀。

---

## 5. Go / no-go 表

| verdict | **SOFT-GO** |
|---|---|
| Why soft | PV 已归因；add2 主目标清晰；与 AdaStatic/EncFp8/LlmRmsQ **正交**；有可写的新核设计 |
| Why 默认不合 | **今日无 glue 可测**；须 FlashRT 新核；e2e 先验 <1 ms；不挡 15Hz 叙事 |
| 何时升级 GO 测 | residual_add_layer_norm_fp8（或 to_out residual epi）落地可编 pack 后，same-session A/B + gate |
| Do **not** | 碰 QK dtype；重开 DitAttnE4/DitLayout/L2/V1/VisNonV1；把 PV 误算进「只融 add」；自批合入 |

---

## 6. Method 对照（本轮做了什么）

| 步骤 | 结果 |
|---|---|
| 读 v3 DitSoftAdd + AdaStatic 外推 | ✅；并 **补发** AdaStatic denoise_loop nsys |
| 设计 / 最小 wire | 设计 ✅；**无最小 wire**（无现成核） |
| same-session A/B stages+e2e | **未跑**（无 cand pack） |
| accuracy gate | **未跑**（同上） |
| Verdict | **SOFT-GO**，默认不合，不自批 |

---

## 7. Artifacts

| | |
|---|---|
| Report (thor) | `/work/gr00t_fp8_phase_a/ditsoftadd_scout/gr00t-ditsoftadd-scout.md` |
| Report (shared) | `/home/nio/shared/gr00t-fp8/gr00t-ditsoftadd-scout.md` |
| nsys parse | `ditsoftadd_nsys_baseline_parse.json` |
| kern CSV | `ditsoftadd_adastatic_kern_sum.csv` / `ditsoftadd_scout/nsys/*` |
| Script | `run_ditsoftadd_nsys_baseline.sh` |

