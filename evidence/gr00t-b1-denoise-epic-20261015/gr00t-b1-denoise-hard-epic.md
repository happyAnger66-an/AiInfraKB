# GR00T B1 — Denoise 硬啃 epic（开题 / inventory + 首刀设计）

- Date: 2026-10-15 ~11:50 Asia/Shanghai
- Status: **开题报告**；**未 wire / 未编新 pack / 不合基线**（首刀设计就绪，默认定稿后另批落地）
- 晓安哥拍：**B1+B2**；本文件只覆盖 **B1 Denoise 硬啃**（B2 Vision Soft 另开）
- Baseline lock：**L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi**  
  → e2e_full **89.772** / denoise_loop **43.953** / gap ≈ **23.1 ms**（vs 66.7）
- Thor: `thor-2239` / `pi05-forge-agent`；`FLASHRT_ROOT=/srcs/data/FlashRT`
- 验收口径：e2e_full；cos>0.999 ∧ mse<0.0005；**禁 2-step**；**禁**重开 VisNonV1 / L2 / AttnScore plain / DitLayout
- Soft 先例修订：本 B1 **允许新核 epic**（DitSoftAdd Soft 曾「默认不合、不挖核」→ 本 epic 升 GO 路径）

---

## 0. 一句话结论

| | |
|---|---|
| **锁基线 denoise GPU** | **45.788 ms/loop**（Cg4 pack nsys；墙钟 loop 43.95 ≈ launch 税已被 Cg4 吃掉大半） |
| **主墙** | **FP8 cutlass GemmUniversal 25.43（55.5%）** + layout 8.24 + QK/softmax/add ≈ 7.2 |
| **Epic 三刀** | `DitGemm` / `DitSoftAdd`（`res_ln_fp8` glue↑新核备） / `DitAttnE4` |
| **估合计 Δe2e** | 现实 **−1～−4**；乐观投机（含 DitGemm 大成）**−3～−10** → 仍难稳到 66.7 |
| **推荐第一落地刀** | **`DitSoftAdd`**（现成 `flashrt.res_ln_fp8` **glue**，非新挖核） |
| **本任务交付** | 本报告 + Cg4 nsys parse；**不强制合入** |

---

## 1. 锁基线 denoise_loop nsys 分桶（+Cg4；SiluEpi 不改 DiT）

Capture: `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_cg4_unirt`  
warm3 / iters12 / lockfreq GATE / `--cuda-graph-trace=node` + `cudaProfilerApi`  
Artifacts: `b1_nsys_cg4_baseline_parse.json` / `b1_cg4_denoise_loop_kern_sum.csv`

| bucket | ms/loop | L/loop | % GPU | B1 关系 |
|---|---:|---:|---:|---|
| **fp8_gemm**（GemmUniversal e4m3） | **25.430** | **672** | **55.5%** | **DitGemm** 主墙 |
| **layout**（reshape/transpose/cast） | **8.236** | 556 | 18.0% | DitLayout NO-GO；E4 可吃 `transpose3_reshape` 边 |
| **attn_qk_f32**（magma） | **2.631** | 128 | 5.7% | **禁** AttnScore 重放 |
| **attn_softmax**（已 fused+cast） | **2.375** | 128 | 5.2% | SoftAdd **不**再融 softmax（已融；与 add 不相邻） |
| **elem_add** | **2.173** | 320 | 4.7% | **DitSoftAdd**：add2 **1.366**/L64 + add3 0.807/L256 |
| take（残留） | 1.805 | 48 | 3.9% | D1take 后边角；非本 epic 主刀 |
| **layer_norm_fp8** | **0.666** | 128 | 1.5% | SoftAdd 融合对象（与 add2 相邻） |
| **ada_ln_fp8** | **0.603** | 128 | 1.3% | Ada 已预计算+fp8；再抠 ROI 薄 |
| gelu_fp8 | 0.572 | 128 | 1.2% | 已融 |
| **attn_pv**（wmma+nvjet） | **0.737** | ~140 | 1.6% | SoftAdd 仅 fused-attn 才动；非本首刀 |
| **quantize**（to_out Q） | **0.379** | 144 | 0.8% | **DitAttnE4** |
| fp16_nvjet / other | 0.18 | — | <0.5% | `proj_out_2` 等边角（DitRes Soft，非 B1 主） |
| **GPU total** | **45.788** | — | 100% | vs AdaStatic SoftAdd nsys 46.645（−0.86，噪声/Cg4 捕获差） |

### 对照墙钟

| | AdaStatic（pre-Cg4） | **+Cg4 lock** |
|---|---:|---:|
| wall denoise_loop | ~49.2–49.7 | **43.953** |
| GPU nsys /loop | 46.645 | **45.788** |
| Cg4 收益落点 | — | **墙钟 −5～−6**（launch/sync）；**内核桶几乎同构** |

→ B1 硬啃对象是 **内核工作量**（尤其 25.4 GEMM），不是再抠 cudagraph。

### Ada / Softmax / add / PV / GEMM 焦点（ms）

| 焦点 | ms | 备注 |
|---|---:|---|
| GEMM | **25.43** | tile 模板见下 |
| Softmax | 2.38 | 已 fused；与 add **隔着 PV+pack+to_out** |
| elem_add | 2.17 | SoftAdd 主目标 = **add2 1.37** |
| PV | 0.74 | 归因 probs@V（SoftAdd scout 已钉） |
| Ada（ada_ln_fp8） | 0.60 | 环内调制读；bank 预计算已消 |
| quantize | 0.38 | E4 目标 |

---

## 2. Epic 清单

### 2.1 `DitGemm` — FP8 cutlass GemmUniversal 再挖

| | |
|---|---|
| **目标** | 砍 **~25.4 ms/loop** 的 `cutlass::GemmUniversal` e4m3 墙（L=672 = 168 Linear/step ×4；crosskv 已 −96 vs 768） |
| **现状核** | SM100 TMA UMMA；tile **`256×128×64`**；`float_e4m3_t`×`float_e4m3_t`→`half`；epi **`LinCombPerColBias`**（偏置融合已有） |
| **估 Δe2e_full** | 现实 **−1～−4**；乐观投机 **−2～−8**（inventory）；**未证实** |
| **依赖** | ① 按 Linear **形状账**（M,N,K / 每 step launches）拆桶；② ncu 抽样算力 vs 带宽；③ tvm_fp8_gemm_unified / cutlass 选 tile·split-K·cluster；④ same-session A/B |
| **工程量** | **重**：1–3+ 人周量级（测 → 调参 → 可能改 so / 重编 DiT）；专家向 |
| **风险** | **高**：已是 FP8 TC 主路径；再抠可能 **0 / 负**；易与精度/对齐/workspace 纠缠；**不当首刀** |
| **不做** | 减步；换整套 attn；重开 L2/VisNonV1 |

**子路径（设计 only）**

1. **DitGemm-Shape**（measure）：导出 672 launches 的 (M,N,K) 直方图 + 每 shape 均时 → 标「小 M 税 / 大 GEMM」。
2. **DitGemm-Tune**：对占时 top shapes 试 alternate tile / split-K / 2SM 配置（若 so 暴露旋钮）。
3. **DitGemm-Epi**：to_out residual epi（与 SoftAdd P1 备选重叠）— 排期二选一。

---

### 2.2 `DitSoftAdd` — residual ⊕ LayerNorm→e4m3（**升 GO glue**）

| | |
|---|---|
| **目标** | 消 **add2 ~1.37**（+对应 launch），把 `hidden += attn_out` 与紧随的 `layer_norm_fp8(norm3)` 合成一发 |
| **关键修正** | Soft scout 写「无现成 residual+LN_fp8 核」**过时**：**`flashrt.res_ln_fp8` 已在**（`layer_norm_fp8.cuh` 通用 `res_ln_fp8_kernel_f16` + π0 SigLIP 接线先例；d1152 特化之外有通道路径，**DiT hidden=1536 可走 generic**） |
| **估 Δe2e_full** | **−0.2～−0.8**（与 Soft 修订一致；天花板 ≈ add2） |
| **依赖** | mlc-vla `BasicTransformerBlock.forward` glue；`MLC_VLA_GR00T_DIT_SOFTADD=1`（默认 0）；**FlashRT 已有核 → 本刀默认不挖新核**；备选才是 synapsex 特化 |
| **工程量** | **轻–中**：0.5–1 d glue + 编 DiT pack + lockfreq A/B + gate（对齐历史小刀） |
| **风险** | **中低**：数值非 bit-identical（融 LN+Q）；须 overall gate；ada_norm 下 norm3 无 affine（已有 ones/zeros 喂法，与现 `layer_norm_fp8` 路径同构） |
| **边界** | **不**动 softmax / QK / PV；**不**重开 DitLayout；FFN 后 `+ ff_out`（add3）本刀可不啃 |

**接线草稿（已定位）** — `modules_dit.py` ≈ L459–479：

```text
# 今日
hidden = hidden + attn_out          # add2
x_q = layer_norm_fp8(hidden, …)    # 0.67
ff_out = ff.forward_from_prequant(x_q)
return hidden + ff_out

# SoftAdd
res, x_q = res_ln_fp8(hidden, attn_out, w, b, scale, eps)
ff_out = ff.forward_from_prequant(x_q)
return res + ff_out
```

**成功标准（若批落地）**

| 项 | 门槛 |
|---|---|
| overall gate | cos>0.999 ∧ mse<0.0005 vs lock DiT |
| stages | same-session Δe2e_full **≤ −0.2** 才算正；目标带 −0.3～−0.8 |
| nsys | **add2 L 64→0**（或大幅↓）；`layer_norm_fp8` L 与新 `res_ln_fp8` 此消彼长；**softmax/QK/PV 不变** |
| 开关 | flag=0 回落 bit-identical 旧路径 |

---

### 2.3 `DitAttnE4` — fused BNTH→BTD + e4m3（清 to_out Q）

| | |
|---|---|
| **目标** | 消 **quantize ~0.38**（L≈144，主为 A2 to_out）；PV 后 pack **直出 e4m3 BTD** |
| **估 Δe2e_full** | **−0.2～−0.6**（scout 修订；勿用旧 inventory −0.5～−2） |
| **依赖** | **新核** `dit_pack_out_fp8` / `fused_bnth_to_btd_quantize`（FlashRT/synapsex）；mlc-vla `_attention` + `_to_out_maybe_prequant` 跳过独立 Q |
| **工程量** | **中**：核 0.5–1 d + shim + 编包测 |
| **风险** | **中**：π0 F2b「Q 融进重 attn epi 会亏」→ **只做轻 layout→e4**，禁止塞进 FA/PV；与 SoftAdd to_out-residual-epi 备选可能打架 |
| **不做** | AttnScore f16 logits；搬 `varlen_attn_fp8out`；重开 `DIT_LAYOUT=1` 整包 |

**成功标准（若批）**：quantize L **144→≤16**（理想 0）；`fused_transpose3_reshape*` 被新核替换；gate PASS；Δe2e 落 −0.2～−0.6。

---

## 3. 推荐第一落地刀

| | |
|---|---|
| **ID** | **`DitSoftAdd`** |
| **形态** | **现成核 glue scout → 测过再合**（非立刻全量 epic wire） |
| **为何第一** | ① 因果钉死（add2↔LN_fp8 相邻）；② **核已在**（Soft→GO 成本陡降）；③ 与 DitGemm/E4 **正交**；④ 工程最轻、可 gate；⑤ Gemm 硬啃需先 Shape measure，不宜盲调 |
| **本开题任务** | **只交设计 + nsys**；落地另批（或架构师一句话 GO 后牛马开 glue） |
| **并行可开（不挡）** | **DitGemm-Shape** measure（纯 inventory，无合入） |

### 首刀成功标准（摘要）

1. flag 接线 + 新/改 DiT pack（Cg4 栈叠加 SoftAdd）  
2. lockfreq same-session vs Cg4+SiluEpi lock：e2e/loop Δ 落估带  
3. overall PASS  
4. nsys：add2 消、softmax/QK/GEMM 桶不恶化  

### Epic 排序建议

```text
DitSoftAdd (glue)  →  DitAttnE4 (新核填缝)  →  DitGemm-Shape → DitGemm-Tune
        ↑ 第一刀              ↑ SoftAdd 后        ↑ 可与 SoftAdd 并行 measure
```

---

## 4. 估总 Δ 与 15Hz 现实

| 组合 | 估 Δe2e | 落地后 e2e（相对 89.8） |
|---|---:|---:|
| SoftAdd only | −0.2～−0.8 | ~89.0～89.6 |
| SoftAdd + E4 | −0.4～−1.4 | ~88.4～89.4 |
| + DitGemm 现实 | −1.5～−5 | ~85～88 |
| + DitGemm 乐观投机 | −3～−10 | ~80～87 |
| **B1+B2 再叠 Vision Soft** | 另 −0～−3 | 仍 **远大于 66.7** |

→ B1 是 **正确的硬缺口方向**，但 **单 epic 填不满 ~23 ms**；需与 B2 / 未来图级路径一起看，不承诺本轮 15 Hz。

---

## 5. 明确不做（本 epic）

| 禁 | 原因 |
|---|---|
| 2-step / 减步 | 产品禁 |
| VisNonV1 / V1 plain / L2 / AttnScore / DitLayout | 已 NO-GO |
| SoftAdd 误融 softmax 或吞 PV 当填缝 | 不相邻 / 越界 FA |
| DitAttnE4 搬 F2b flash fp8out | 几何不符 + 历史亏 |
| 未做 Shape 账就大改 cutlass so | 投机过高 |
| 本开题直接合基线 | 任务默认设计 only |

---

## 6. Artifacts

| | |
|---|---|
| **本报告** | `/home/nio/shared/gr00t-fp8/gr00t-b1-denoise-hard-epic.md` |
| nsys parse | `b1_nsys_cg4_baseline_parse.json` |
| kern CSV | `b1_cg4_denoise_loop_kern_sum.csv` |
| 脚本 | `/work/gr00t_fp8_phase_a/run_b1_cg4_nsys_baseline.sh` |
| 前序 Soft/E4 | `gr00t-ditsoftadd-scout.md` / `gr00t-ditattn-e4-scout.md` |
| 基线 | `CURRENT_BASELINE.md`（e2e 89.772） |

---

## 7. Ask（给架构师 / 晓安哥）

1. 批 **DitSoftAdd** 为 B1 第一落地刀（`res_ln_fp8` glue）？  
2. **DitGemm-Shape** 是否与 SoftAdd **并行 measure**？  
3. DitAttnE4 排 SoftAdd 之后填缝，还是与 SoftAdd 抢 to_out epi 需先裁？
