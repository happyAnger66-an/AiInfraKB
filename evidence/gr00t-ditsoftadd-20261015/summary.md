# GR00T DitSoftAdd scout — 证据摘要

来源：牛马 `gr00t-ditsoftadd-scout.md`（2026-10-15）；AdaStatic 新基线 nsys 钉名 + PV 归因 + 设计草稿。**未改代码 / 未编 pack / 未跑 stages·overall A/B**。

## Verdict

| 项 | 值 |
|---|---|
| 决策 | **SOFT-GO / 默认不合** |
| 估 Δe2e_full | **−0.2～−0.8 ms**（inventory −0.3～−1.0 略偏乐观） |
| 基线 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic；e2e_full 95.513 |
| GPU | softmax 已融 **2.40**；elem_add **2.27**（add2 **1.39** 主目标）；PV **0.79** |
| 今日可测 | 否（无现成 residual+LayerNorm_fp8 核） |

## 一句话

Softmax+cast **已经 fused**。它和 residual add 中间隔着 **PV → pack → to_out(+Q)**，不相邻，不能靠再融一行 `op.add` 吃掉 softmax。正道是新核 **`residual_add_layer_norm_fp8`**（DiT 是 LayerNorm，不能搬 RMS residual），或 **to_out FP8 GEMM residual epi**。相对 gap ~28.8 ms 是填缝。

## 架构师口径

默认不合，记设计 backlog；勿碰 QK dtype；勿把 PV 算进「只融 add」；勿重开 AttnScore / DitAttnE4 / DitLayout。

全文见同目录 `gr00t-ditsoftadd-scout.md`。
