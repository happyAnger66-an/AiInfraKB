# GR00T 15Hz — gap inventory v3（相对新锁基线，批下一刀）

- Date: 2026-10-15 Asia/Shanghai (~09:54)
- Status: **measure/scout inventory only**；**不改代码 / 不合基线 / 不 commit**
- 验收口径（gr00t-optimize-gate）：**e2e_full ≈ 66.7 ms（15 Hz）**；overall cos>0.999 且 mse<0.0005；禁 2-step/减步；优先量化/融合/算子/预计算
- **当前锁基线**：**L1+L3+D1+crosskv+D1take+AdaStatic** → e2e_full **99.347** / e2e_head **60.090** / denoise_loop **49.236**
- 别名：`gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt`
- Gap：**~32.65 ms**（99.35 − 66.7）
- Thor: `thor-2239` / `pi05-forge-agent`；锁频 gpc=1575 / nvd=1692 GATE PASS（历史测）
- 主刀方针（架构师）：π0 易搬菜单基本吃完；下一拍标清 **Vision 非 V1、attn→e4m3、LLM 其它税**；别闲着但别盲开
- 对照：v2 `gr00t-15hz-gap-inventory-v2.md`（L1+L3+D1+crosskv ~103.5）；本 v3 叠入 **D1take+AdaStatic 合入** + DitRes Soft-GO

---

## 0. 相对 v2 的变更摘要

| 项 | v2（~09:30） | **v3（本表）** |
|---|---|---|
| 基线 | L1+L3+D1+crosskv ~103.5 | **L1+L3+D1+crosskv+D1take+AdaStatic ~99.35** |
| 已合新刀 | L3 | **+D1take（−1.21）+AdaStatic（叠 −2.17）** |
| Soft-GO 新结论 | D1take 排队 | **DitRes Soft-GO / 默认不合**（估修订 −0.1～−0.5） |
| 已 NO-GO（不变） | AttnScore / DitLayout / L2 / V1 / V1b / steps2 | 同左；**勿重开** |
| Gap | ~37 ms | **~32.6 ms** |
| π0 预计算菜单 | AdaStatic / D1take 待吃 | **基本吃完**（D1+crosskv+bank+step+static bake） |

---

## 1. Stages vs 66.7（权威墙钟 — 新锁基线）

来源：`CURRENT_BASELINE.md` / `gr00t-adastatic-merge.md` / `adastatic_merge_measure_summary.json`；warmup=8 iters=40；lockfreq。

| stage | p50 ms | share of e2e | vs 66.7 直觉 |
|---|---:|---:|---|
| embed_vision | **19.056** | 19% | 仍 FP16 ViT；**V1 回归 / V1b 薄利不合**；仅非 V1 路径可议 |
| backbone_llm | **19.989** | 20% | L1 GU + L3 o/down FP8；**QKV 仍 FP16**（L2 NO-GO） |
| encode_condition | **6.799** | 7% | 未动 |
| **denoise_loop** | **49.236** | **50%** | D1+crosskv+D1take+AdaStatic；4-step；**仍主缺口桶** |
| denoise_step | 16.501 | — | 单步（含环内；环外 bake 已进） |
| e2e_head | 60.090 | — | ≈16.6 Hz（head **已过** 15Hz；full 未过） |
| **e2e_full** | **99.347** | 100% | **距 66.7 ≈ −32.6 ms** |

Accuracy vs prior D1take pack：cos=0.999999 / mse=1.59e-6 / PASS。

### 缺口落点

| bucket | ms | 备注 |
|---|---:|---|
| denoise_loop alone | 49.2 | **已占 66.7 预算的 74%** — 即便 Vision+LLM=0，encode+loop≈56 仍贴边 |
| Vision+LLM+encode | 45.8 | 另占预算 69% |
| **必须双边砍** | −32.6 | 单舞台刀不够；denoise 仍主线，bb 只吃合规新路径 |

示意拆分（非承诺）冲 66.7：vision ~10 + llm ~12 + enc ~5 + loop ~36 + oh ~3 ≈ 66。  
今日：19.1 + 20.0 + 6.8 + 49.2 + ~4 → 需大约 **vis −9 / llm −8 / enc −2 / loop −13**。

相对 v2（需 loop −20）：AdaStatic+D1take 已从 loop 抠走 ~4–5 ms；**loop 仍要再砍约 13 ms** 才够「示意拆分」——且该拆分本身已极乐观。

---

## 2. denoise_loop 热图（外推；AdaStatic 后未重捕 nsys）

基线 nsys：`dr_crosskv_bench`（D1+crosskv，GPU ~48.5 ms/loop）。  
已知墙钟 Δ：D1take loop **−1.07**（bit-identical）；AdaStatic 叠 D1take loop **−2.36**（合入）/ 孤立 **−3.35**。  
→ 新基线 wall loop **49.2**；下列 GPU 桶为 **D1+crosskv 减去已知预计算收益后的外推**，**非**新 nsys。下一刀 dig 前建议补一发 AdaStatic+D1take nsys。

| bucket | ~ms/loop（外推） | % | 状态 / 下一刀关系 |
|---|---:|---:|---|
| **FP8 cutlass GemmUniversal** | **~25** | ~52% | 已 FP8；硬啃 = **DitGemm**（投机） |
| **layout**（reshape/transpose/cast；take 已削） | **~8–10** | ~18–22% | DitLayout **NO-GO**；AttnScore **未吃 cast**；剩 attn pack 税 |
| attn QK **FP32 magma** | **~2.6** | ~5% | AttnScore f16 **NO-GO**（loop≈0）；勿重放 |
| attn softmax+cast | **~2.4** | ~5% | 已 fused；再融 → **DitSoftAdd** |
| attn PV（wmma/nvjet f16） | **~0.7** | ~1.5% | 非 QK；属 SoftAdd / 非 DitRes |
| **quantize_fp8**（A2 `to_out`） | **~0.41** | ~0.9% | 清税正道 = **attn→e4m3（DitAttnE4）** |
| elem add | **~2.3** | ~5% | residual / AdaLN 旁路 |
| **环外 nvjet_192×8（AdaLN bank）** | **~0**（已砍） | — | **AdaStatic ✅** |
| bank 行 `take_kernel`×256 | **~0**（已砍） | — | **D1take ✅** |
| 残留 FP16 Linear `proj_out_2` | **~0.06** | — | **DitRes Soft-GO**（天花板矮） |

**一句话：** 预计算菜单（D1 / crosskv / take / static）**已落地**；loop 剩下的大块是 **FP8 GEMM 墙 ~25** + **layout/attn pack ~8–10** + **QK f32 / softmax / add ~7**；可合规小刀（AttnE4 / SoftAdd / DitRes）合计乐观仍个位数 ms。

---

## 3. π0.5 已成刀 → GR00T 搬迁账（v3 更新）

| π0.5 杠杆 | GR00T 现状 | v3 动作 |
|---|---|---|
| 静态 FP8 大覆盖 | DiT full_dit ✅；bb **L1+L3** ✅ | ✅ 主覆盖到位 |
| `geglu/gelu_fp8` + prequant | DiT A1 ✅；LLM Silu→e4m3 **无现成核** | LLM fused Silu = **核债**（非主刀） |
| `ada_rms_fp8` / `ada_ln_fp8` | ✅ | ✅ |
| `precompute_adarms` | **D1** ✅ | ✅ |
| cross K/V 预计算 | **crosskv** ✅ | ✅ |
| ada **bank+step** | **D1take** ✅ 合入 | ✅ |
| **0034 static Ada 表** | **AdaStatic** ✅ 合入 | ✅ |
| KV / dit pack layout | **DitLayout NO-GO** | ❌ 勿重放 |
| attn `logits_dtype` f16 | **AttnScore NO-GO** | ❌ |
| SigLIP `gelu_fp8` / BiasGeluE4m3 | **V1 回归 / V1b 薄利不合** | ❌ 不重放；只列 **非 V1** |
| cudagraph + materialize | **Cg4** 弱正/无害 | 可选合 |
| 降步 4→2 | **禁** | ❌ |

**一句话：** π0「覆盖 + 融合 Q + Ada/cross 预计算 + static bake」主菜单 GR00T **已吃完**；剩下要么是 **π0 未直接给的硬骨头**（attn→e4m3、layout 真消、FP8 GEMM 再挖、Vision/LLM 非 plain 路径），要么是 **核债**（Silu epi / rms_fp8）。

---

## 4. 尚未搬且合规的候选（估 Δe2e_full；相对 ~99.35）

优先级：**P0 = 架构师点名大块 / denoise 新路径**；P1 = 薄利或可选；P2 = 投机 / 核债。

| pri | ID | 杠杆 | 估 Δe2e_full | 风险 | 依赖 | 建议 |
|---|---|---|---:|---|---|---|
| **P0** | **DitAttnE4** | attn 出口 / pack **直出 e4m3**（清 `to_out` 前 quantize ~0.41；可能连带减 cast） | **−0.5～−2.0?** | 中–高（epi/pack；精度；可能新核） | nsys 钉 A2 Q；mlc-vla ± synapsex；**非** AttnScore 重放 | **主推 dig**：架构师点名 **attn→e4m3** |
| **P0** | **VisNonV1**（暂名 **V2attn**） | Vision **非 V1 plain**：ViT **attn QKV/proj FP8 + shared Q**（π0 SigLIP attn 路径）；**禁止**再拆 bias+gelu | **−2～−5?** | 中（calib；ViT 敏感层） | 先证 π0 有可迁 attn fused；**不**重测 V1/V1b | **scout-only**；架构师点名 Vision 非 V1 |
| **P0** | **LlmTax**（拆两支） | **(a) LlmRmsQ**：RMS→e4m3 **共享**进 QKV（**不是** L2 plain 换核）；（b）Silu→e4m3 fused epi（核债） | **(a) −0.5～−2?** / **(b) −1～−3?** | (a) 中（L2 教训：税易吃光）；(b) 高（无核） | nsys 证 QKV 税；rms_fp8 / silu epi | **先 (a) scout**；架构师点名 **LLM 其它税** |
| **P1** | **DitSoftAdd** | softmax/cast 与 elem-add 再融 / 减 launch（含 PV 归因清楚后再动） | **−0.3～−1.0** | 中（新核或 Relax） | 新 nsys；勿碰 QK dtype | Ada/AttnE4 不够时 |
| **P1** | **EncFp8** | encode_condition FP8 / 融合 | **−0.5～−2** | 低 | calib | denoise/LLM 主线后再开 |
| **P1** | **Cg4** | cudagraph@4（已批无害） | **~0～−1** | 极低 | pack flag | **随时可合**，不挡主刀 |
| **P1** | **DitRes** | `proj_out_2` → FP8（± norm_out→e4m3） | **−0.1～−0.5** | 低 | calib；**不消** quantize 0.41 | **Soft-GO backlog**；默认不合 |
| **P2** | **DitGemm** | FP8 cutlass ~25 ms 再挖（tile/split-K/algo） | **−2～−8?** | **高**（投机） | cutlass 专家 + 新 nsys | **scout-only**；勿当填缝 |

### 乐观加总（合规 P0，未证实）

| 组合 | 估合计 | 落地后 e2e |
|---|---:|---:|
| DitAttnE4 + DitSoftAdd + DitRes + Cg4 | **~1～4** | **~95～98** |
| 再加 EncFp8 + LlmRmsQ 乐观 | **+1～4** | **~91～97** |
| 再加 VisNonV1（V2attn）乐观 | **+2～5** | **~86～95?** |
| 再加 DitGemm 乐观 | **+2～8?** | **~78～93?**（未证实） |

→ **即令 P0 全成且偏乐观，距 66.7 仍约 15–30+ ms。** 现约束下「合规小刀堆叠」**冲不满** e2e_full；须另开更大路径（产品/结构/图级）或接受阶段性目标。与架构师「π0 可搬菜单已基本吃完」一致。

---

## 5. 明确不要做（已 NO-GO / Soft backlog / 禁）

| ID / 动作 | 为何不做 / 何时可开 | 证据 |
|---|---|---|
| **steps2 / 降步** | 产品禁；vs 4-step FAIL | dparallel；gate |
| **V1 plain** | embed **+1.5～+2.2** 回归 | `gr00t-v1-vision-mlp-report.md` |
| **V1b 默认合** | 仅 −0.5～−1.2；feature cos 软；**不合默认**；仅当 VisNonV1 挖空且仍要 −1 时可复议 | `gr00t-v1b-fused-epi-report.md` |
| **L2 QKV FP8 plain** | e2e 仅 −0.75；cutlass+税吃 nvjet | `gr00t-l2-qkv-fp8-report.md` |
| **DitLayout** / `DIT_LAYOUT=1` | denoise **+1.9**；pack 换皮不消 | `gr00t-dit-layout-scout.md` |
| **AttnScore**（f16 logits） | loop≈0 / e2e −0.85；cast 税未吃 | `gr00t-attn-score-cross-f16.md` |
| **DitRes 当主刀** | Soft-GO；真残留几乎只 `proj_out_2`；估 **−0.1～−0.5**；**默认不合**；Ada+D1take 后若仍抠小数且磁盘闲可升测 | `gr00t-ditres-scout.md` |
| 指望 take* 全桶 = D1take | 已合；天花板本就 ~0.46 | D1take report |
| 重放 AdaStatic / D1take | **已合入基线** | merge md |
| 用 **e2e_head** 冒充 full 验收 | 晓安哥定 **e2e_full**（head 已 ~60 过 66.7） | gate |
| 把路线写成再开 V1 / L2 / AttnScore | 已 NO-GO | 架构师纠偏 |

---

## 6. 基线组件速查（合入 / 不合）

| 组件 | 包 / flag | e2e 贡献（量级） | 默认 |
|---|---|---:|---|
| DiT phase_ada_ln | `..._phase_ada_ln_*` | loop 1.26× vs FP16 | ✅ |
| D1 AdaLN precomp | `ADA_LN_PRECOMP` | loop **−4.9** | ✅ |
| crosskv | `CROSS_KV_PRECOMP` | loop **−2.0** | ✅ |
| **D1take** | `ADA_LN_BANK_STEP` | e2e **−1.21** | ✅ |
| **AdaStatic** | `ADA_LN_STATIC` / `static_ada_ln_bank` | e2e 叠 **−2.17** | ✅ |
| L1 LLM MLP FP8 | `..._l1_llm_mlp_i4` | llm 大块 | ✅ |
| L3 o/down FP8 | `..._l3_o_down_i4` | e2e **−4.2** | ✅ |
| L2 QKV | `..._l2_*` | −0.75 | ❌ |
| V1 / V1b | vit packs | 负 / −0.5 | ❌ |
| AttnScore f16 | `..._attn_score_f16` | −0.85 / loop 0 | ❌ |
| DitRes | 未实现 | Soft-GO −0.1～−0.5 | ❌ backlog |
| cudagraph@4 | `--cuda-graph` | 弱正 | 可选 |

---

## 7. 给架构师：推荐下一刀 ID（2–3）

| # | 短名 | 一句话 |
|---|---|---|
| **1** | **DitAttnE4** | attn 出口/pack **→ e4m3**，清 `to_out` quantize ~0.41 并探 cast 税（估 e2e **−0.5～−2?**）；点名大块，**非** AttnScore 重放。 |
| **2** | **LlmRmsQ** | RMS→e4m3 **共享**进仍 FP16 的 LLM QKV（估 **−0.5～−2?**）；点名 **LLM 其它税**，**禁止**重放 L2 plain。 |
| **3** | **VisNonV1 / V2attn** | Vision **非 V1**：ViT attn QKV/proj FP8+shared Q scout（估 **−2～−5?**）；先证 π0 可迁，**禁止**再开 V1 plain / 默认 V1b。 |

**建议批法：** 先批 **DitAttnE4 scout**（denoise 主线、与 SoftAdd 边界划清）；并行 **LlmRmsQ nsys+设计**（bb 税）；**VisNonV1** 做「π0 可迁清单」再决定是否 wire。  
**DitGemm / EncFp8 / Cg4 / DitRes** 不进本轮主 ID，除非 1–3 测完仍要抠且有方案。

**现实核对：** 1+2+3 乐观合计仍约 **3–9 ms** → e2e **~90–96**，**冲不到 66.7**。继续堆合规刀是正确姿势，但 full 15Hz 需要架构师另开路径讨论（本 inventory **不**提案 steps/图产品变更）。

---

## 8. Artifacts / 指针

| 文件 | 用途 |
|---|---|
| **本报告** | `/home/nio/shared/gr00t-fp8/gr00t-15hz-gap-inventory-v3.md` |
| v2 / v1 | `gr00t-15hz-gap-inventory-v2.md` / `gr00t-15hz-gap-inventory.md` |
| 新基线 | `CURRENT_BASELINE.md` / `gr00t-adastatic-merge.md` |
| D1take | `gr00t-d1-take-fuse-report.md` / `gr00t-d1-take-merge.md` |
| DitRes Soft-GO | `gr00t-ditres-scout.md` |
| AttnScore NO-GO | `gr00t-attn-score-cross-f16.md` |
| DitLayout NO-GO | `gr00t-dit-layout-scout.md` |
| Vision/LLM 早期 scout | `gr00t-15hz-vision-llm-scout.md` |
| nsys（旧） | `nsys_baseline_parse.json` / `gap_meta.json` / `d1_take_nsys_ab.json` |

---

## 9. Ask

1. 批下一主 ID：**DitAttnE4** scout 是否开？（与 DitSoftAdd 边界：E4 清 Q，SoftAdd 融 softmax/add）  
2. **LlmRmsQ** 与 **VisNonV1** 是否并行 scout，还是串行？  
3. 是否要求先补一发 **新基线 denoise_loop nsys**（AdaStatic+D1take）再 dig？
