# GR00T EncFp8 — 证据摘要（scout + merge）

来源：牛马 scout + `gr00t-encfp8-merge.md`（2026-10-15）；scout Soft-GO，架构师升 GO 批合并锁基线。

## Scout（vs L3，隔离 Enc）

| 项 | 值 |
|---|---|
| encode_condition | **−1.388** |
| e2e_full | −0.407 |
| overall | cos 0.999979 / mse 5.03e-5 PASS |
| nsys | `fp8_gemm`×480；`gelu_fp8`×80；`layer_norm_fp8`×80；fp16_nvjet 500→100 |
| 决策 | Soft-GO，默认不合（可升 GO 吃 encode） |

## Merge sanity（锁新基线）

| 项 | 值 |
|---|---|
| Stack | L1+L3+**LlmRmsQ**+**EncFp8**+D1+crosskv+D1take+AdaStatic |
| e2e_full | **95.513**（vs LlmRmsQ session −2.731） |
| encode_condition | 6.615→5.177（**−1.438**）**刀账** |
| denoise_loop | −1.074（DiT 未改，会话噪声） |
| overall | cos 0.999999 / mse **2.723e-6** PASS |
| bb 别名 | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQEnc_unirt` |
| SHA | `7d9fd34cd3bbd9d71d36413a5775a7aa672aff22` |
| Gap | 距 66.7 仍 ~**28.8 ms** |
| 未动 | state_encoder / vlln |

权威墙钟以 cand **95.513** 为准；刀收益以 **encode_condition −1.438** 为准。

全文：`gr00t-encfp8-scout.md` / `gr00t-encfp8-merge.md`。
