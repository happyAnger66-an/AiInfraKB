# GR00T B1 Denoise 硬啃 epic — 证据摘要

来源：牛马 `gr00t-b1-denoise-hard-epic.md`（2026-10-15 ~11:50）；Cg4 pack nsys 分桶 + 三刀设计。**未 wire / 未编新 pack / 不合基线。** 晓安哥拍 B1+B2；本文件只覆盖 B1。

## 基线与主墙

| 项 | 值 |
|---|---|
| 锁栈 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi |
| e2e_full | **89.772**；墙钟 denoise_loop **43.953**；gap ≈ **23.1 ms**（vs 66.7） |
| denoise GPU | **45.788 ms/loop**（Cg4 nsys；AdaStatic SoftAdd nsys 46.645） |
| fp8_gemm | **25.430**（55.5%，L=672）— **DitGemm** 主墙 |
| layout | **8.236**（18.0%） |
| elem_add | **2.173**（add2 **1.366** / L64）— **DitSoftAdd** |
| layer_norm_fp8 | **0.666**（与 add2 相邻） |
| quantize | **0.379** — **DitAttnE4** |

Cg4 收益在墙钟 launch（loop 约 49.2–49.7 → **43.953**）；内核桶几乎同构。硬啃对象是内核工作量。

## Epic

| 刀 | 估 Δe2e | 排期 |
|---|---|---|
| DitSoftAdd（现成 `flashrt.res_ln_fp8` glue） | −0.2～−0.8 | **第一刀**；修订 kb-0018「无核」 |
| DitAttnE4 | −0.2～−0.6 | SoftAdd 之后 |
| DitGemm | 现实 −1～−4；乐观 −2～−8 | **后置**（先 Shape measure） |
| 三刀合计 | 现实 **−1～−4**；乐观 **−3～−10** | 仍冲不满 66.7 |

## 架构师口径

**GO SoftAdd first**（glue，默认不挖新核）。DitGemm 不当首刀。禁 2-step；禁重开 VisNonV1 / V1 plain / L2 / AttnScore / DitLayout。

全文见同目录 `gr00t-b1-denoise-hard-epic.md`。
