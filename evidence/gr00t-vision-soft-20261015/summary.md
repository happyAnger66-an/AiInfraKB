# GR00T Vision Soft — 证据摘要（scout + glue+measure）

来源：牛马 scout（2026-10-15 ~12:00）+ `gr00t-vision-soft-measure.md`（~12:47）。scout 当时 Soft-GO、可迁 YES、估中枢 −0.5～−1.5；架构师升 GO glue+measure（in flight）。实测墙钟回退且 embed feature 崩。架构师确认 **NO-GO，不合**。

## Measure（lockfreq A/B + nsys；本刀结论）

| 项 | 值 |
|---|---|
| 决策 | **NO-GO / 不合**（勿进 CURRENT；工作树 Soft glue 可留实验，未 commit） |
| embed_vision | 18.886 → **19.256（+0.370）** |
| e2e_full | 88.638 → **88.806（+0.168）** |
| overall | cos **1.0** / mse **0** **PASS**（相对 gate，**不链式** embed→LLM→action） |
| embed feature cos | **0.417938**（约 0.418；崩） |
| backbone_llm | bit-identical（Soft 不碰 LLM） |
| nsys | `res_ln_fp8` **HIT** ~3.715 ms/iter；half_in **PARTIAL MISS**（`kQuantizeHalfToE4m3` ~0.39 ms/iter）；nvjet f16 bias ~8.492→~0.649 **丢掉**；cutlass GEMM ~4.464→~8.703 |
| 相对 scout | 估 −0.5～−1.5 **符号相反** |
| 对照 | 同 session SiluMul lock bb vs Soft；DiT = Cg4。denoise_* 记会话噪声；刀账是 embed / e2e_full |

preset `e4m3_gr00t_llm_l3_qkv_enc_vit_soft`（232 = 136+96）。pack `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_vit_soft_i4_unirt`（新名字，不覆盖锁 bb alias）。

## Scout（当时未 wire；估带已被实测取代）

| 项 | 值 |
|---|---|
| 决策（当时） | scout **Soft-GO**（默认可开 glue+measure，默认不合入）；架构师升 **GO glue+measure（in flight）** |
| 可迁 | **YES**（`res_ln_fp8` + `vit_fp8_o_half_in`；hidden 1024 走通用 f16） |
| 估 Δembed_vision / Δe2e_full | **−0～−2.5 ms**（中枢 **−0.5～−1.5**） |
| 锁基线（scout 时） | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi；e2e_full **89.772** / embed_vision **19.338** |
| 清税对象 | VisNonV1 独立 `quantize_fp8` ~0.57 ms/iter（embed +1.37 / e2e +1.48，已 NO-GO） |

可迁仍成立。被取代的是「glue 后墙钟会落到估带、合入另批」——实测不合，见 **kb-0024**。

## 架构师口径

**NO-GO 确认。** 勿回 VisNonV1 / V1 plain。勿把 overall PASS 当 Vision 质量门。勿把 Soft 写入 CURRENT。勿声称 Soft 填满 66.7。禁 2-step。Thor/LT5 工作树 Soft glue **可留实验**。续挖数值挂 Soft backlog（real-act calib、deepstack residual，再修 half_in BYOC）。下一刀 **DitGemm-Shape（measure only）**。B1 DitSoftAdd 不受本结论阻塞。

全文：`gr00t-vision-soft-scout.md` / `gr00t-vision-soft-measure.md`。
