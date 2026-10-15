# GR00T LlmRmsQ — 证据摘要（scout + merge）

来源：牛马 scout + `gr00t-llmrmsq-merge.md`（2026-10-15）；架构师升 GO 批合并锁基线。

## Scout

| 项 | 值 |
|---|---|
| e2e_full | 99.940 → 97.916（**−2.024**） |
| backbone_llm | −1.638 |
| overall | cos 0.999810 / mse 4.580e-4 PASS（贴门） |
| nsys | `rms_fp8` HIT；QKV nvjet 768→0 |

## Merge sanity（锁新基线）

| 项 | 值 |
|---|---|
| Stack | L1+L3+**LlmRmsQ**+D1+crosskv+D1take+AdaStatic |
| e2e_full | **98.432**（vs pre −1.750） |
| llm | 18.924（−1.334） |
| head / loop | 60.680 / 49.691 |
| overall | cos 0.999939 / mse **1.465e-4** PASS（比 scout 松） |
| bb 别名 | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` |
| Gap | 距 66.7 仍 ~**31.7 ms** |

`w−1` Soft-GO 可跟不挡；下一刀 EncFp8。

全文：`gr00t-llmrmsq-scout.md` / `gr00t-llmrmsq-merge.md`。
