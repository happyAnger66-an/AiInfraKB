# GR00T LlmRmsQ — RMS→e4m3 共享进 QKV 证据摘要

来源：牛马 `gr00t-llmrmsq-scout.md`（2026-10-15）；架构师 **升 GO，批合**（scout 原 Soft-GO 默认不合）。

## Verdict

| 项 | 值 |
|---|---|
| 决策 | **GO / 批合**（合入 sanity 待牛马） |
| e2e_full | 99.940 → **97.916（−2.024）** |
| backbone_llm | 20.166 → **18.528（−1.638）** |
| overall | cos 0.999810 / mse 4.580e-4 **PASS**（贴门） |
| nsys | `rms_fp8` HIT；QKV nvjet 768→0；FP8 GEMM 1024→1792 |

估锁新基线 ~97.3（叠现锁 ~99.35）；`w−1` Soft-GO 可跟，不挡合入。

## vs L2

L2 = RMS FP16 + 独立 `quantize_fp8`（e2e −0.75，NO-GO）；本刀 = **`rms_fp8`→shared prequant**（非 L2）。

## 下一刀

架构师批 **EncFp8** scout（禁 L2/V1/AttnScore/DitAttnE4 核债重开）。

全文见同目录 `gr00t-llmrmsq-scout.md`。
