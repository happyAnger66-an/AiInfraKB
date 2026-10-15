# GR00T LlmSiluEpi — 证据摘要（design scout + merge）

来源：牛马 design scout + `gr00t-llmsiluepi-merge.md`（2026-10-15）；scout Soft-GO，架构师升 **GO glue**（不挖 GEMM-epi）后合入。

## Scout（设计-only，未编 pack）

| 项 | 值 |
|---|---|
| 现成核 | FlashRT `silu_mul_split_fp8_fp16`（真 SiLU×up→e4m3） |
| 缺口 | UniRT/synapsex 无封装；**无** SM100 Silu GEMM epi |
| 估 Δ llm / e2e | **−0.3～−1.0**（inventory −1～−3 偏乐观，下修） |
| 决策 | Soft-GO，默认不合；**禁** merge gate_up / 新 Silu GEMM epi |

L1 后 `fused_silu_multiply` 已融；本刀只消 down 入口独立 Q。

## Merge sanity（锁新基线）

| 项 | 值 |
|---|---|
| Stack | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+**LlmSiluEpi** |
| e2e_full | 90.210 → **89.772**（**−0.438**） |
| backbone_llm | 18.265 → 17.619（**−0.646**） |
| overall | cos **0.999952** / mse **1.152e-4** PASS |
| llm feature | cos ~0.84 soft；**非** bit-identical |
| synapsex | `06783a8e8384cfaf0edf687a1be30a0e236a61fa`（薄 so） |
| mlc-vla | `ad3cc2bac2a4198d95fc036c1d2c9005a47f52d9`（Qwen3MLP glue） |
| Gap | 距 66.7 仍 ~**23.1 ms** |

权威墙钟以 cand **89.772** 为准；刀收益落 scout 带内。denoise_loop +0.69 为 DiT 未改的会话噪声。架构师：合规小刀菜单到此关闭。

全文：`gr00t-llmsiluepi-design-scout.md` / `gr00t-llmsiluepi-merge.md`；基线摘录：`CURRENT_BASELINE-siluepi.md`。
