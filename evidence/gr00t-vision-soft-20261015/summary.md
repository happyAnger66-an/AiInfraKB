# GR00T Vision Soft scout — 证据摘要

来源：牛马 `gr00t-vision-soft-scout.md`（2026-10-15 ~12:00）；可迁证明 + 估 Δ。**未 wire / 未编包 / 不合入。**

## Verdict

| 项 | 值 |
|---|---|
| 决策 | scout **Soft-GO**（默认可开 glue+measure，**默认不合入**）；架构师升 **GO glue+measure（in flight）** |
| 可迁 | **YES**（`res_ln_fp8` + `vit_fp8_o_half_in`；hidden 1024 走通用 f16） |
| 估 Δembed_vision / Δe2e_full | **−0～−2.5 ms**（中枢 **−0.5～−1.5**；bb-only，同量级） |
| 锁基线 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi；e2e_full **89.772** / embed_vision **19.338** |
| 清税对象 | VisNonV1 独立 `quantize_fp8` **~0.57 ms/iter**（embed **+1.37** / e2e **+1.48**，已 NO-GO） |
| 相对 66.7 | 满成仍 ~87–90；**冲不满** |

## 一句话

π0 `res_ln_fp8` + `vit_fp8_o_half_in` 可迁到 GR00T ViT（pre-LN 同构，核已在 mlc-vla FlashRT）。目标是杀掉 VisNonV1 的独立 Q 税并吸收 residual+LN，不是再跑 plain Linear。可迁 = 可搬 glue，不是现成 flag。

## 架构师口径

升 **GO glue+measure**（in flight，测量未回、仍默认不合入）。禁 VisNonV1 / V1 plain；禁 2-step。合入另按 embed 与 overall 门控批。

全文见同目录 `gr00t-vision-soft-scout.md`。
