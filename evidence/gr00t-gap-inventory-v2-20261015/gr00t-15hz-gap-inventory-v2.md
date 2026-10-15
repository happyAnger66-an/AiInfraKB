# GR00T 15Hz — gap inventory v2（对照 π0.5，批下一刀）

- Date: 2026-10-15 Asia/Shanghai (~09:30+)
- Status: **measure/scout inventory only**；**不改代码 / 不合基线 / 不 commit**
- 验收口径（晓安哥拍板）：**e2e_full ≈ 66.7 ms（15 Hz）**
- 当前合入基线：**L1+L3+D1+crosskv** → e2e_full **~103.5 ms** / e2e_head **~63–64 ms** / denoise_loop **~53–55 ms**
- Gap：**~37 ms**（103.5 − 66.7）
- Thor: `thor-2239` / `pi05-forge-agent`；锁频 gpc=1575 / nvd=1692 GATE PASS
- 主刀方针（架构师）：**denoise 深挖优先**（loop 占 full 一半）；禁止降步/2-step；禁止重放 V1 plain；**AttnScore 已 NO-GO**
- Vision：仅当 π0.5 有**尚未搬完**的可迁 fused 路径再列入 scout（V1/V1b 已测过）
- 对照：v1 `gr00t-15hz-gap-inventory.md`（L1+D1+crosskv，~108）；本 v2 叠入 L3 合入 + AttnScore/DitLayout/D1-take 结论

---

## 0. 相对 v1 的变更摘要

| 项 | v1（~23:50） | **v2（本表）** |
|---|---|---|
| 基线 | L1+D1+crosskv ~108 | **L1+L3+D1+crosskv ~103.5** |
| 已合新刀 | — | **L3 o/down FP8（−4.2 e2e）** |
| 已 NO-GO 新刀 | L2 / V1 / V1b / DitLayout / steps2 | + **AttnScore cross-f16** |
| Soft-GO 排队 | — | **D1-take（bank+step）**；可选 **cudagraph@4** |
| Gap | ~41 ms | **~37 ms** |
| 验收 | 当时未定 | **e2e_full**（晓安哥） |

---

## 1. Stages vs 66.7（权威墙钟）

来源：L3 scout same-session（`stages_l3_o_down.json`）；warmup=8 iters=40；lockfreq。

| stage | p50 ms | share of e2e | vs 66.7 直觉 |
|---|---:|---:|---|
| embed_vision | **19.4** | 19% | 仍 FP16 ViT（V1 回归 / V1b −0.9 不合） |
| backbone_llm | **20.2** | 20% | L1 GU + **L3 o/down** FP8；**QKV 仍 FP16** |
| encode_condition | **6.8** | 7% | 未动 |
| **denoise_loop** | **53.1** | **51%** | D1+crosskv；4-step；**主缺口桶** |
| denoise_step | 15.8 | — | 单步无环外 precomp |
| e2e_head | 64.2 | — | ≈15.6 Hz（head 已近） |
| **e2e_full** | **103.5** | 100% | **距 66.7 ≈ −37 ms** |

### 缺口落点

| bucket | ms | 备注 |
|---|---:|---|
| denoise_loop  alone | 53 | **已占 66.7 预算的 80%** — 即便 Vision+LLM=0，encode+loop≈60 仍贴边 |
| Vision+LLM+encode | 46.4 | 另占预算 70% |
| **必须双边砍** | −37 | 单舞台刀不够；denoise 深挖是主线，bb 只吃合规薄利 |

示意拆分（非承诺）：vision ~12 + llm ~14 + enc ~5 + loop ~33 + oh ~3 ≈ 67。  
今日：19.4 + 20.2 + 6.8 + 53.1 + ~3 → 需大约 **vis −7 / llm −6 / enc −2 / loop −20**。

---

## 2. denoise_loop nsys 热图（D1+crosskv；L3 不改 DiT）

捕获：`dr_crosskv_bench/nsys`（12 iters）；GPU **~48.5 ms/loop**。L3 只动 bb，DiT 桶仍适用。

| bucket | ms/loop | % GPU | L/loop | 状态 |
|---|---:|---:|---:|---|
| **FP8 cutlass GemmUniversal** | **25.0** | 52% | 672 | 已 FP8；硬啃需 alg/tile/融合，非「再套一层 preset」 |
| **layout**（reshape/transpose/cast/take） | **10.6** | 22% | 860 | DitLayout **NO-GO**；AttnScore **未吃到 cast** |
| attn QK **FP32 magma** | **2.64** | 5.5% | 128 | AttnScore cross-f16 **NO-GO**（loop≈0） |
| attn softmax+cast | **2.41** | 5.0% | 128 | 已 fused；再融需新设计 |
| **FP16 nvjet** | **2.56** | 5.3% | 114 | 其中 **nvjet_192×8 ≈2.05 / 33L = D1 AdaLN bank 环外** |
| elem add | 2.25 | 4.7% | 320 | residual / AdaLN 旁路 |
| quantize_fp8 | 0.41 | 0.9% | 144 | 税已很低（π0 式融合大半完成） |

**layout 内 take* 解剖（DitLayout / D1-take scout）：**

| 片 | ms/loop | 可否本轮 dig |
|---|---:|---|
| attn reshape/transpose/cast (A+B+C+D) | ~8.2 | DitLayout 已负 ROI；AttnScore 未兑现 cast → **勿重放** |
| `take_kernel`×256（`_take_mod_row`） | **~0.46** | **D1-take Soft-GO** 目标 |
| `take4/5` 大行 | ~1.45 | **另归因**；不是 AdaLN bank |
| 其它 | 余 | 小 |

**环外仍付费：** D1 把 AdaLN Linear 提出 loop，但 **每 loop 仍付 nvjet_192×8 ~2.05 ms** 做 bank（M=N=4）。π0.5 **0034 static AdaRMS 表** 类路径可进一步把固定 Euler t 的调制 **bake 进 pack**，环内/环外都只读。

---

## 3. π0.5 已成刀 → GR00T 搬迁账

| π0.5 杠杆 | π0 效果（量级） | GR00T 现状 | v2 动作 |
|---|---|---|---|
| 静态 FP8 大覆盖（QKVO+MLP+down） | e2e ~1.22× | DiT full_dit 已开；bb **L1+L3** 已开 o/down | ✅ 主覆盖到位 |
| `geglu_fp8` / `gelu_fp8` + prequant | 消 Q 税 | DiT A1 gelu_fp8 ✅；LLM Silu→e4m3 **无现成核** | DiT 完；LLM fused Silu epi = 核债（非主刀） |
| `ada_rms_fp8` + shared Q | 消 AdaLN 后 Q | **`ada_ln_fp8`**（公式不同，已落地）✅ | ✅ |
| `precompute_adarms` | 环外 skinny GEMV | **D1** ✅（−4.9 loop） | ✅ |
| cross K/V 预计算 | 省重复 GEMM | **crosskv / DR** ✅（−2.0 loop） | ✅ |
| `ada_rms` **bank+step**（shim 行指针） | 删图上 take | **D1-take Soft-GO** 未实现 | **P0 填缝** |
| **0034 static Ada 表**（固定 t bake） | 更大预计算 | **未搬** | **P0 候选（AdaStatic）** |
| KV / dit pack layout | 专用 pack | 已 port → **DitLayout NO-GO**（SIMT 负 ROI） | ❌ 勿重放 |
| attn `logits_dtype` f16 | score GEMM | **AttnScore 已测 NO-GO** | ❌ |
| SigLIP `gelu_fp8` / BiasGeluE4m3 | ViT MLP | **V1 回归 / V1b −0.5～−1.2 不合** | ❌ 默认不列；无「新」fused 待搬 |
| cudagraph + materialize | loop 再砍 | **cudagraph@4** 已测弱正/无害 | 可选合 |
| 降步 4→2 | 大砍 | **产品禁 / vs 4-step FAIL** | ❌ **banned** |

**一句话：** π0.5 的「覆盖 + 融合 Q + Ada/cross 预计算」主菜单 GR00T **大半已落地**；剩下可搬且合规的，主要是 **更深预计算（bank+step / static bake）**、**残量 epi/Linear**、以及 **FP8 GEMM 本身再挖**（难）。Vision fused 路径已试过，不是新缺口。

---

## 4. 尚未搬且合规的候选（估 Δe2e_full）

优先级：**P0 = denoise**；P1 = bb 薄利 / 可选；P2 = 投机或依赖核债。

| pri | ID | 杠杆 | 估 Δe2e_full | 风险 | 依赖 | 建议 |
|---|---|---|---:|---|---|---|
| **P0** | **D1take** | AdaLN bank **+step** 进 `ada_ln_fp8`（删 256×`op.take`）；对齐 π0 shim | **−0.3～−0.8** | 低（可 bit-identical） | FlashRT shim / synapsex 同等 step；**不**挡其它刀 | **落地 Soft-GO**（架构师已排①） |
| **P0** | **AdaStatic** | 固定 Euler t **bake** 调制表 / proj 行（π0 0034）；砍环外 **nvjet_192×8 ~2.05** + 相关 gather | **−1.5～−3.5** | 中（pack/loader；t 表与 config 绑死） | D1 已合；与 D1take 正交可叠 | **主推下一「大」预计算刀** |
| **P0** | **DitRes** | 环内残留 FP16 Linear（`proj_out_2` 等）→ FP8 或 `norm_out→e4m3`；清残留 quantize ~0.4 | **−0.5～−1.5** | 低–中（精度门） | calib；nsys 先钉核名 | denoise 小刀；可并行 scout |
| **P0** | **DitSoftAdd** | softmax/cast 与 elem-add 再融 / 减 launch（非 AttnScore） | **−0.3～−1.0** | 中（需新核或 Relax 证明） | nsys 归因；勿碰 QK dtype | 仅当 AdaStatic/DitRes 不够时 |
| **P0?** | **DitGemm** | FP8 cutlass 25 ms 再挖（tile/workspace/split-K/algo） | **−2～−8?** | **高**（投机；易零收益） | nsys+cutlass 专家；勿改精度覆盖 | **scout-only 先**；勿当填缝 |
| P1 | **EncFp8** | encode_condition FP8 / 融合 | **−0.5～−2** | 低 | calib | denoise 主线后再开 |
| P1 | **Cg4** | cudagraph@4（已批无害） | **~0～−1**（旧测 loop 可更大，hybrid 噪声） | 极低 | 单独 pack flag | **随时可合**，不挡主刀 |
| P1 | **LlmRmsQ** | RMS→e4m3 **共享**进残留 QKV（**不是**重放 L2 plain） | **−0.5～−2?** | 中（L2 教训：换核税易吃光） | 需 `rms_fp8` 类核；nsys 证净利 | 仅当 nsys 证明 tax 主导 |
| P2 | **V\*** | Vision **新** fused（非 V1 plain / 非再测 V1b） | speculative | 高 | 须先证明 π0 有**未搬** fused；今日 **无** | **不列入本轮 scout** |

### 乐观加总（合规 P0）

| 组合 | 估合计 | 落地后 e2e |
|---|---:|---:|
| D1take + AdaStatic + DitRes | **~2.5～6** | **~97.5～101** |
| 再加 DitSoftAdd + Enc + Cg4 | **+1～4** | **~94～100** |
| 再加 DitGemm 乐观 | **+2～8?** | **~86～98?**（未证实） |

→ **即令 P0 全成，距 66.7 仍约 20–30+ ms。** 现约束下「小刀堆叠」冲不满 e2e_full；须另开路径（产品/结构）或接受阶段性目标。这与架构师「即便 AttnScore+D1-take 全成也只再抠 1–4 ms」同向，但 **AdaStatic** 把预计算天花板抬到数 ms 级，仍远不够 37。

---

## 5. 明确不要做（已 NO-GO / 负 ROI / 禁）

| ID / 动作 | 为何不做 | 证据 |
|---|---|---|
| **steps2 / 降步** | 产品禁；vs 4-step PT overall FAIL | dparallel 报告 |
| **V1 plain**（拆 bias+gelu→独立 gelu_fp8） | embed **+1.5～+2.2** 回归 | `gr00t-v1-vision-mlp-report.md` |
| **V1b 默认合** | 仅 −0.5～−1.2；feature cos 软；架构师不合默认 | `gr00t-v1b-fused-epi-report.md` |
| **L2 QKV FP8** | e2e 仅 −0.75；cutlass+税吃 nvjet | `gr00t-l2-qkv-fp8-report.md` |
| **DitLayout** 重开 / `DIT_LAYOUT=1` | 已知 denoise **+1.9**；pack 换皮不消 | `gr00t-dit-layout-scout.md` |
| **AttnScore**（含 self 全 f16 / 再调 cast） | cross-f16：**loop≈0 / e2e −0.85**；cast 税未吃 | `gr00t-attn-score-cross-f16.md` |
| 指望 take* **2.27 ms 全桶** = D1-take | 天花板只 ~0.46 bank 行 | `gr00t-d1-take-fuse-scout.md` |
| 重放「安全 ff6 / 只扩 QKV」冲 1.3× | 覆盖数学上限 ~1.04× | status π0 对照 |
| 用 **e2e_head** 冒充 full 验收 | 晓安哥定 **e2e_full** | 微信拍板 |
| 把路线写成 **L1→V1→D1** | **V1 已 NO-GO**；基线是 L1+L3+D1+crosskv | 架构师纠偏 |

---

## 6. 基线组件速查（合入 / 不合）

| 组件 | 包 / flag | e2e 贡献（量级） | 默认 |
|---|---|---:|---|
| DiT phase_ada_ln（gelu/LN/ada_ln/QKV shared） | `..._phase_ada_ln_*` | loop 1.26× vs FP16 | ✅ |
| D1 AdaLN precomp | `ADA_LN_PRECOMP` | loop **−4.9** | ✅ |
| crosskv | `CROSS_KV_PRECOMP` | loop **−2.0** | ✅ |
| L1 LLM MLP FP8 | `..._l1_llm_mlp_i4` | llm 大块 | ✅ |
| L3 o/down FP8 | `..._l3_o_down_i4` | e2e **−4.2** | ✅ |
| L2 QKV | `..._l2_*` | −0.75 | ❌ |
| V1 / V1b | vit packs | 负 / −0.5 | ❌ |
| AttnScore f16 | `..._attn_score_f16` | −0.85 / loop 0 | ❌ |
| cudagraph@4 | `--cuda-graph` | 弱正 | 可选 |
| D1-take | 未实现 | Soft-GO | 排队落地 |

---

## 7. 给架构师：推荐下一刀 ID（2–3）

| # | 短名 | 一句话 |
|---|---|---|
| **1** | **D1take** | 落地 Soft-GO：`ada_ln_fp8(..., step)` 删 bank 行 take（估 e2e **−0.3～−0.8**）；填缝、低风险、已排①。 |
| **2** | **AdaStatic** | 搬 π0 **0034**：固定 4-step t bake AdaLN/proj 表，砍环外 **nvjet_192×8 ~2 ms**（估 **−1.5～−3.5**）；当前最大合规 denoise 预计算刀。 |
| **3** | **DitRes** | 钉死环内残留 FP16 Linear（`proj_out_2` 等）+ 残 quantize→FP8/epi（估 **−0.5～−1.5**）；可与 1/2 并行 scout。 |

**建议批法：** 先批 **D1take 实现+测**（短）；并行开 **AdaStatic scout**（设计+估+是否动 loader）；**DitRes** 做 nsys 钉名后再决定是否 wire。  
**DitGemm** 不进本轮 ID，除非 AdaStatic 测完仍要啃 25 ms FP8 墙且有 cutlass 方案。

**现实核对（再写一遍）：** 1+2+3 乐观合计仍约 **3–6 ms** → e2e **~97–100**，**冲不到 66.7**。继续堆合规小刀是「别闲着」的正确姿势，但 15Hz full 需要架构师另开路径讨论（本 inventory 不提案 steps/图产品变更）。

---

## 8. Artifacts / 指针

| 文件 | 用途 |
|---|---|
| 本报告 | `/home/nio/shared/gr00t-fp8/gr00t-15hz-gap-inventory-v2.md` |
| v1 | `gr00t-15hz-gap-inventory.md` |
| L3 | `gr00t-l3-o-down-scout.md`（基线 ~103.5） |
| AttnScore NO-GO | `gr00t-attn-score-cross-f16.md` |
| DitLayout NO-GO | `gr00t-dit-layout-scout.md` |
| D1-take Soft-GO | `gr00t-d1-take-fuse-scout.md` |
| D1 / crosskv | `gr00t-d1-residual-gemm-report.md` / `gr00t-denoise-residual-fuse-report.md` |
| nsys parse | `nsys_baseline_parse.json` / `gap_meta.json` |
| π0 对照 | `gr00t-fp8-status.md` §π0.5；`wechat_pending_pi05_vs_gr00t_fp8.txt` |
| V1/V1b/L2 | `gr00t-v1-*.md` / `gr00t-l2-qkv-fp8-report.md` |

---

## 9. Ask

1. 批下一主 ID：**AdaStatic** scout 是否与 **D1take** 落地并行？  
2. **DitRes** 是否进并行 scout，还是等 AdaStatic 设计出后再开？  
3. 确认 Vision **本轮不 scout**（无未搬 fused）— 与「仅 π0 可迁 fused」一致。
