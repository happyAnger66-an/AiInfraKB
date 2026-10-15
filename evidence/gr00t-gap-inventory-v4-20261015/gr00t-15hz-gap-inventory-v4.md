# GR00T 15Hz — gap inventory v4（相对 +EncFp8 新基线，批下一刀）

- Date: 2026-10-15 Asia/Shanghai (~11:05)
- Status: **measure/inventory only**；**不改代码 / 不合基线 / 不 commit**
- 验收口径（gr00t-optimize-gate）：**e2e_full ≈ 66.7 ms（15 Hz）**；overall cos>0.999 且 mse<0.0005；禁 2-step/减步；优先量化/融合/算子/预计算
- **当前锁基线**：**L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic** → e2e_full **95.513** / e2e_head **58.667** / denoise_loop **49.714**
- 别名 bb：`gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` → `..._l3_qkv_rmsq_enc_i4_unirt`；DiT：`..._D1take_AdaStatic_unirt`
- Gap：**~28.8 ms**（95.513 − 66.7）
- Thor: `thor-2239` / `pi05-forge-agent`；锁频 gpc=1575 / nvd=1692 GATE PASS（历史测）
- 主刀方针（架构师）：π0 预计算菜单已吃完；LlmRmsQ+EncFp8 已合；**禁** L2/V1/AttnScore/DitAttnE4 核债重开；DitSoftAdd 另有 scout
- 对照：v3 `gr00t-15hz-gap-inventory-v3.md`（~99.35）；本 v4 叠入 **LlmRmsQ + EncFp8 合入** + VisNonV1 NO-GO + DitAttnE4 Soft 修订

---

## 0. 相对 v3 的变更摘要

| 项 | v3（~09:54） | **v4（本表）** |
|---|---|---|
| 基线 | L1+L3+D1+crosskv+D1take+AdaStatic ~99.35 | **+LlmRmsQ+EncFp8 ~95.51** |
| 已合新刀 | D1take+AdaStatic | **+LlmRmsQ（merge −1.75）+EncFp8（encode −1.44；merge e2e −2.73 vs LlmRmsQ session）** |
| Soft/NO-GO 新结论 | DitRes Soft；DitAttnE4/VisNonV1/LlmRmsQ 仍候选 | **DitAttnE4 Soft（估修订 −0.2～−0.6，默认不合）**；**VisNonV1 NO-GO（+1.48）**；LlmRmsQ/EncFp8 ✅ 合入 |
| 已 NO-GO（不变） | AttnScore / DitLayout / L2 / V1 / V1b / steps2 | 同左 + **VisNonV1**；**勿重开** |
| Soft backlog | DitRes | **DitRes + DitAttnE4 Soft**；Vision Soft（π0 清税路径，非 VisNonV1 plain） |
| Gap | ~32.6 ms | **~28.8 ms** |
| π0 / bb 菜单 | Ada/cross 预计算吃完；点名 attn/LLM/Vision | **bb 主税（RmsQ+Enc）已吃**；denoise 剩 SoftAdd / Soft E4 / Res / GEMM |

Git 原子 commit（已合刀）：L3 `a9ed9e51` → LlmRmsQ `2d0df4ee` → EncFp8 `7d9fd34`；DiT backlog D1/`7b081f3` crosskv/`ce92fb5` D1take/`b518b72` AdaStatic/`e0758e6`。

---

## 1. Stages vs 66.7（权威墙钟 — CURRENT_BASELINE / EncFp8 merge）

来源：`CURRENT_BASELINE.md` / `gr00t-encfp8-merge.md` / `encfp8_merge_measure_summary.json`；warmup=8 iters=40；lockfreq。  
**数字均为合入 sanity cand，非外推。**

| stage | p50 ms | share of e2e | vs 66.7 直觉 |
|---|---:|---:|---|
| embed_vision | **19.083** | 20% | 仍 FP16 ViT；**V1 / VisNonV1 均回归**；仅 π0 清税新路径可议 Soft |
| backbone_llm | **18.568** | 19% | L1 GU + L3 o/down + **LlmRmsQ**；Silu→e4m3 仍核债 |
| encode_condition | **5.177** | 5% | **EncFp8 ✅**（merge Δencode −1.438）；state_encoder/vlln 未动 |
| **denoise_loop** | **49.714** | **52%** | D1+crosskv+D1take+AdaStatic；4-step；**仍主缺口桶** |
| denoise_step | 16.464 | — | 单步（含环内；环外 bake 已进） |
| e2e_head | 58.667 | — | ≈17.0 Hz（head **已过** 15Hz；full 未过） |
| **e2e_full** | **95.513** | 100% | **距 66.7 ≈ −28.8 ms** |

Accuracy vs pre-Enc LlmRmsQ bb：cos=0.999999 / mse=2.723e-6 / PASS。

### 相对 v3 舞台 Δ（权威墙钟对照）

| stage | v3（AdaStatic lock） | **v4（+LlmRmsQ+Enc）** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.056 | 19.083 | ~0（会话抖） |
| backbone_llm | 19.989 | **18.568** | **~−1.4**（LlmRmsQ） |
| encode_condition | 6.799 | **5.177** | **~−1.6**（EncFp8） |
| denoise_loop | 49.236 | 49.714 | ~+0.5（会话噪声；DiT 未改） |
| e2e_full | 99.347 | **95.513** | **~−3.8** |

> EncFp8 merge 记：denoise_loop −1.07 / e2e_head −1.71 为会话噪声；刀收益以 **encode −1.44** 为准。LlmRmsQ 权威以 merge e2e **98.432**（vs L3 session）为准，再叠 Enc → **95.513**。

### 缺口落点

| bucket | ms | 备注 |
|---|---:|---|
| denoise_loop alone | 49.7 | **已占 66.7 预算的 75%** — 即便 Vision+LLM=0，encode+loop≈54.9 仍贴边 |
| Vision+LLM+encode | 42.8 | 另占预算 64% |
| **必须双边砍** | −28.8 | 单舞台刀不够；denoise 仍主线，bb 只剩核债/Soft |

示意拆分（非承诺）冲 66.7：vision ~10 + llm ~12 + enc ~5 + loop ~36 + oh ~3 ≈ 66。  
今日：19.1 + 18.6 + 5.2 + 49.7 + ~3 → 需大约 **vis −9 / llm −7 / enc ~0 / loop −14**。

相对 v3（需 loop −13）：bb 已再抠 ~3–4 ms；**loop 仍要再砍约 14 ms** 才够「示意拆分」——且该拆分本身已极乐观。

---

## 2. denoise_loop 热图（外推；EncFp8 后 DiT 未改，仍无新 nsys）

基线 nsys：`dr_crosskv_bench`（D1+crosskv，GPU ~48.5 ms/loop）。  
已知墙钟：D1take / AdaStatic 已合；Enc/LlmRmsQ **不改 DiT**。  
→ 新基线 wall loop **49.7**；下列 GPU 桶仍为 **D1+crosskv 减去预计算收益后的外推**，**非**新 nsys。DitSoftAdd dig 前建议补一发 AdaStatic+D1take nsys。

| bucket | ~ms/loop（外推） | % | 状态 / 下一刀关系 |
|---|---:|---:|---|
| **FP8 cutlass GemmUniversal** | **~25** | ~52% | 已 FP8；硬啃 = **DitGemm**（投机） |
| **layout**（reshape/transpose/cast；take 已削） | **~8–10** | ~18–22% | DitLayout **NO-GO**；剩 attn pack 税 |
| attn QK **FP32 magma** | **~2.6** | ~5% | AttnScore f16 **NO-GO**；勿重放 |
| attn softmax+cast | **~2.4** | ~5% | 已 fused；再融 → **DitSoftAdd**（并行 scout） |
| attn PV（wmma/nvjet f16） | **~0.7** | ~1.5% | 非 QK；属 SoftAdd / 非 DitRes |
| **quantize_fp8**（A2 `to_out`） | **~0.41** | ~0.9% | **DitAttnE4 Soft**（估修订薄；默认不合） |
| elem add | **~2.3** | ~5% | residual / AdaLN 旁路 → SoftAdd 边界 |
| 环外 AdaLN bank / take | **~0**（已砍） | — | AdaStatic + D1take ✅ |
| 残留 FP16 Linear `proj_out_2` | **~0.06** | — | **DitRes Soft backlog** |

**一句话：** 预计算 + bb 主税已落地；loop 大块仍是 **FP8 GEMM ~25** + **layout/attn pack ~8–10** + **QK/softmax/add ~7**；合规小刀（SoftAdd / Soft E4 / DitRes / Cg4）乐观合计仍个位数 ms。

---

## 3. π0.5 已成刀 → GR00T 搬迁账（v4 更新）

| π0.5 杠杆 | GR00T 现状 | v4 动作 |
|---|---|---|
| 静态 FP8 大覆盖 | DiT full_dit ✅；bb **L1+L3+LlmRmsQ+Enc** ✅ | ✅ 主覆盖到位 |
| `geglu/gelu_fp8` + prequant | DiT A1 ✅；LLM Silu→e4m3 **无现成核** | LLM fused Silu = **核债**（非主刀） |
| `ada_rms_fp8` / `ada_ln_fp8` | ✅ | ✅ |
| `precompute_adarms` / cross K/V / bank+step / static | **D1+crosskv+D1take+AdaStatic** ✅ | ✅ |
| LLM RMS→e4m3 shared QKV | **LlmRmsQ** ✅ | ✅（`w−1` Soft 可跟不挡） |
| encode VL-SA FP8 | **EncFp8** ✅ | ✅；state_encoder/vlln 不挖 |
| KV / dit pack layout | **DitLayout NO-GO** | ❌ |
| attn `logits_dtype` f16 | **AttnScore NO-GO** | ❌ |
| SigLIP / ViT plain + attn plain | **V1 / VisNonV1 NO-GO** | ❌；仅 Soft backlog：π0 `res_ln_fp8` / `vit_fp8_o_half_in` 清税 |
| cudagraph + materialize | **Cg4** 弱正/无害 | 可选合 |
| 降步 4→2 | **禁** | ❌ |

**一句话：** π0「覆盖 + 融合 Q + Ada/cross 预计算 + static bake + bb RmsQ/Enc」主菜单 GR00T **已吃完**；剩下要么是 **denoise 融合小刀**（SoftAdd / Soft E4 / Res）、**核债**（Silu epi）、要么是 **投机硬啃**（DitGemm）。

---

## 4. 尚未搬且合规的候选（估 Δe2e_full；相对 ~95.51）

优先级：**P0 = denoise 在途/主缺口**；P1 = 薄利或可选；P2 = 投机 / 核债 / Soft backlog。

| pri | ID | 杠杆 | 估 Δe2e_full | 风险 | 依赖 | 建议 |
|---|---|---|---:|---|---|---|
| **P0** | **DitSoftAdd** | softmax/cast 与 elem-add 再融 / 减 launch（含 PV 归因清楚后再动）；**非** AttnScore | **−0.3～−1.0** | 中（新核或 Relax） | 新 nsys；勿碰 QK dtype | **并行 scout 在途**；出数再批 |
| **P1** | **Cg4** | cudagraph@4（已批无害；旧测 loop 可 −7，hybrid e2e 噪声大） | **~0～−1**（e2e；loop 曾更大） | 极低 | pack `--cuda-graph`；可选 materialize | **随时可合**，不挡主刀 |
| **P1** | **DitAttnE4 Soft** | attn 出口/pack **直出 e4m3**（清 `to_out` quantize ~0.41） | **−0.2～−0.6**（scout 修订；inventory 旧 −0.5～−2 偏乐观） | 中（需 fused layout→e4 新核） | FlashRT/synapsex；**禁** AttnScore 重放 | **Soft-GO 默认不合**；SoftAdd 不够时填缝 |
| **P1** | **DitRes** | `proj_out_2` → FP8（± norm_out→e4m3） | **−0.1～−0.5** | 低 | calib；**不消** quantize 0.41 | **Soft backlog**；默认不合 |
| **P2** | **LlmSiluEpi** | Silu→e4m3 fused epi（LlmTax b；核债） | **−1～−3?** | **高**（无现成核） | synapsex 新核；nsys 钉 GU 税 | **scout/设计 only**；勿当填缝 |
| **P2** | **Vision Soft backlog** | π0 **清税**路径（`res_ln_fp8` / `vit_fp8_o_half_in`）；**禁止** VisNonV1/V1 plain 再测 | **−0～−3?**（未证实） | 高 | 先证可迁 fused；VisNonV1 已证 plain 回归 | Soft backlog；本轮不主推 |
| **P2** | **DitGemm** | FP8 cutlass ~25 ms 再挖（tile/split-K/algo） | **−2～−8?** | **高**（投机） | cutlass 专家 + 新 nsys | **scout-only**；勿当填缝 |
| **P2** | **w−1 Soft** | LlmRmsQ 的 Gemma `w−1` 适配税（~0.03 ms/iter） | **~0～−0.2** | 极低 | Qwen `rms_fp8_mulw` / fold-LN | Soft 可跟；不挡合入 |

### 已合入（本轮不再估为候选）

| ID | 合入 e2e 贡献（权威） | 备注 |
|---|---:|---|
| LlmRmsQ | **−1.75**（merge vs L3；scout −2.02） | SHA `2d0df4ee` |
| EncFp8 | encode **−1.44**；merge e2e **−2.73** vs LlmRmsQ session（含噪声） | SHA `7d9fd34`；刀收益看 encode |

### 乐观加总（合规剩余，未证实）

| 组合 | 估合计 | 落地后 e2e |
|---|---:|---:|
| DitSoftAdd + DitAttnE4 Soft + DitRes + Cg4 | **~0.6～3.1** | **~92～95** |
| 再加 LlmSiluEpi 乐观 | **+1～3** | **~89～94** |
| 再加 Vision Soft / DitGemm 乐观 | **+2～8?** | **~81～92?**（未证实） |

→ **即令剩余合规刀全成且偏乐观，距 66.7 仍约 15–25+ ms。** 现约束下「合规小刀堆叠」**冲不满** e2e_full；须另开更大路径（产品/结构/图级）或接受阶段性目标。与架构师「π0 可搬菜单已基本吃完」一致。

---

## 5. 明确不要做（已 NO-GO / Soft backlog / 禁）

| ID / 动作 | 为何不做 / 何时可开 | 证据 |
|---|---|---|
| **steps2 / 降步** | 产品禁；vs 4-step FAIL | dparallel；gate |
| **V1 plain** | embed **+1.5～+2.2** 回归 | `gr00t-v1-vision-mlp-report.md` |
| **V1b 默认合** | 仅 −0.5～−1.2；feature cos 软；**不合默认** | `gr00t-v1b-fused-epi-report.md` |
| **VisNonV1**（ViT attn FP8 plain + shared Q） | embed **+1.37** / e2e **+1.48**；quantize 税吃光 GEMM | `gr00t-visnonv1-attn-fp8-scout.md` |
| **L2 QKV FP8 plain** | e2e 仅 −0.75；cutlass+税吃 nvjet | `gr00t-l2-qkv-fp8-report.md` |
| **DitLayout** / `DIT_LAYOUT=1` | denoise **+1.9**；pack 换皮不消 | `gr00t-dit-layout-scout.md` |
| **AttnScore**（f16 logits） | loop≈0 / e2e −0.85；cast 税未吃 | `gr00t-attn-score-cross-f16.md` |
| **DitAttnE4 当主刀 / 重开核债** | Soft-GO；ROI 修订 **−0.2～−0.6**；需新核；架构师禁「核债重开」当主线 | `gr00t-ditattn-e4-scout.md` |
| **DitRes 当主刀** | Soft-GO；真残留几乎只 `proj_out_2`；估 **−0.1～−0.5**；**默认不合** | `gr00t-ditres-scout.md` |
| 重放 AdaStatic / D1take / LlmRmsQ / EncFp8 | **已合入基线** | merge md |
| 挖 state_encoder / vlln | 架构师本轮明确不挖 | EncFp8 批合 |
| 用 **e2e_head** 冒充 full 验收 | 晓安哥定 **e2e_full**（head 已 ~58.7 过 66.7） | gate |
| 把路线写成再开 V1 / VisNonV1 / L2 / AttnScore / DitLayout | 已 NO-GO | 架构师纠偏 |

---

## 6. 基线组件速查（合入 / 不合）

| 组件 | 包 / flag | e2e 贡献（量级） | 默认 |
|---|---|---:|---|
| DiT phase_ada_ln | `..._phase_ada_ln_*` | loop 1.26× vs FP16 | ✅ |
| D1 / crosskv / D1take / AdaStatic | `ADA_LN_*` / `CROSS_KV` / `static_ada_ln_bank` | loop 大块预计算 | ✅ |
| L1 LLM MLP FP8 | `..._l1_llm_mlp_i4` | llm 大块 | ✅ |
| L3 o/down FP8 | `..._l3_o_down_i4` | e2e **−4.2** | ✅ |
| **LlmRmsQ** | `LLM_RMS_FP8` + `LLM_QKV_SHARED_FP8` | e2e **−1.75** | ✅ |
| **EncFp8** | `e4m3_gr00t_llm_l3_qkv_enc` | encode **−1.44** | ✅ |
| L2 QKV plain | `..._l2_*` | −0.75 | ❌ |
| V1 / V1b / VisNonV1 | vit packs | 负 / 薄利不合 / **+1.48** | ❌ |
| AttnScore f16 | `..._attn_score_f16` | −0.85 / loop 0 | ❌ |
| DitAttnE4 | 未实现（需新核） | Soft −0.2～−0.6 | ❌ Soft |
| DitRes | 未实现 | Soft −0.1～−0.5 | ❌ Soft |
| cudagraph@4 | `--cuda-graph` | 弱正 | 可选 |

---

## 7. 给架构师：推荐下一刀 ID（2–3）

| # | 短名 | 一句话 |
|---|---|---|
| **1** | **DitSoftAdd** | denoise 剩最大合规融合桶（softmax/cast/add/PV）；估 e2e **−0.3～−1.0**；**scout 已在途**，出数按 Soft/GO 批合 + 原子 commit。 |
| **2** | **Cg4** | cudagraph@4 无害可选；估 e2e **~0～−1**（loop 曾更大）；随时可合，不挡 SoftAdd，适合升基线后立刻原子 commit。 |
| **3** | **LlmSiluEpi**（设计/scout） | bb 剩核债：Silu→e4m3 fused epi；估 **−1～−3?**；**仅设计+估+是否有核**，勿当填缝主刀；DitAttnE4 Soft / DitRes 仅 SoftAdd 薄利后填缝。 |

**建议批法：** 等 **DitSoftAdd** 出数 → GO 则叠基线 sanity + **原子 commit**；并行可批 **Cg4** 合入（低风险）。**LlmSiluEpi** 只开设计/scout，确认有核再 wire。  
**DitGemm / Vision Soft / DitAttnE4 Soft / DitRes** 不进本轮主 ID，除非 SoftAdd+Cg4 测完仍要抠且有方案。

**现实核对：** 1+2+3 乐观合计仍约 **1.5～5 ms** → e2e **~90–94**，**冲不到 66.7**。继续堆合规刀是正确姿势，但 full 15Hz 需要架构师另开路径讨论（本 inventory **不**提案 steps/图产品变更）。

---

## 8. Artifacts / 指针

| 文件 | 用途 |
|---|---|
| **本报告** | `/home/nio/shared/gr00t-fp8/gr00t-15hz-gap-inventory-v4.md` |
| v3 / v2 / v1 | `gr00t-15hz-gap-inventory-v3.md` / `-v2.md` / `.md` |
| 新基线 | `CURRENT_BASELINE.md` / `gr00t-encfp8-merge.md` / `gr00t-llmrmsq-merge.md` |
| EncFp8 / LlmRmsQ | `gr00t-encfp8-scout.md` / `gr00t-llmrmsq-scout.md` |
| DitAttnE4 Soft | `gr00t-ditattn-e4-scout.md` |
| VisNonV1 NO-GO | `gr00t-visnonv1-attn-fp8-scout.md` |
| DitRes Soft | `gr00t-ditres-scout.md` |
| Cg4 / steps2 | `gr00t-dparallel-report.md` |
| nsys（旧） | `nsys_baseline_parse.json` / `gap_meta.json` / `d1_take_nsys_ab.json` |

---

## 9. Ask

1. **DitSoftAdd** scout 出数后批 GO/NO-GO？（与 DitAttnE4 Soft 边界：SoftAdd 融 softmax/add，E4 清 Q）  
2. **Cg4** 是否与 SoftAdd 合入并行（独立原子 commit）？  
3. 第三刀开 **LlmSiluEpi 设计 scout**，还是先 Soft 填缝（DitAttnE4 Soft / DitRes）？
