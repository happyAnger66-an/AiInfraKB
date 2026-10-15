# GR00T DitAttnE4 scout — 证据摘要

来源：牛马 `gr00t-ditattn-e4-scout.md`（2026-10-15）；架构师批 **SOFT-GO，默认不合、不进本轮主刀**。

## Verdict

| 项 | 值 |
|---|---|
| 决策 | **SOFT-GO / 默认不合** |
| 估 Δe2e_full | **−0.2～−0.6 ms**（inventory −0.5～−2 偏乐观） |
| GPU 天花板 | `quantize_fp8` ~0.41 ms/loop（≤128L ≈ A2 to_out） |
| 今日实测 | 无（无现成 attn→e4m3 核） |
| 基线 | L1+L3+D1+crosskv+D1take+AdaStatic ~99.35 |

## 一句话

A2 已把 `to_out` 接到 FP8 GEMM；剩独立 `quantize_fp8` 薄税。清它要 fused BNTH→BTD+scaled e4m3 新核，再 `forward_prequantized`。**不是** AttnScore；**勿搬** π0 F2b flash fp8out。相对 gap ~32.6 ms 是填缝。

## 架构师

SOFT-GO 确认；P1 fused BTD-e4 核暂不批开工；先等 VisNonV1。~16L 余量本刀不挡、现在也不挖。

全文见同目录 `gr00t-ditattn-e4-scout.md`。
