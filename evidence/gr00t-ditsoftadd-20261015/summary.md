# GR00T DitSoftAdd — 证据摘要（scout + merge）

来源：牛马 scout + `gr00t-ditsoftadd-merge.md`（2026-10-15）。scout 当时 Soft-GO、默认不合，并写「无现成核」。B1 钉 `flashrt.res_ln_fp8` 后架构师升 **GO glue**，**已合入**。scout「无核」由 **kb-0023** 取代。

## Scout（AdaStatic nsys；当时未改代码）

| 项 | 值 |
|---|---|
| 决策（当时） | **SOFT-GO / 默认不合** |
| 估 Δe2e_full | **−0.2～−0.8 ms** |
| 基线 | e2e_full 95.513（EncFp8+AdaStatic，Cg4 之前） |
| GPU | softmax 已融 **2.40**；add2 **1.39**；PV **0.79**；与 residual add 中间隔 PV→pack→to_out |
| 「无核」 | **已过时**。核是现成 `flashrt.res_ln_fp8`，不是再挖 `residual_add_layer_norm_fp8` |

Softmax 已融、与 add 不相邻仍然成立。被修订的只是可 glue。

## Merge sanity（锁新基线）

| 项 | 值 |
|---|---|
| Stack | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd** |
| e2e_full | 88.155 → **87.506**（**−0.649**） |
| denoise_loop | 44.249 → **42.610**（**−1.639**） |
| denoise_step | 14.276 → 13.506（**−0.770**） |
| overall | cos **1.0** / mse **0** / 132/132 **bit-identical PASS** |
| mlc-vla | `03604486355c84939f1133a0af05c1833bff1f3a`（`feat/gelu-fp8-synapsex`） |
| Gap | 距 66.7 仍 ~**20.8 ms** |

权威墙钟以 cand **87.506** 为准。锁基线旧值 89.772 在本 session 抖到 ref 88.155。vision +0.198 / llm +0.223 是会话噪声；刀账是 denoise_loop **−1.639** / e2e **−0.649**，落 scout −0.2～−0.8。未动 QK/softmax/PV；未挖 DitGemm。

全文：`gr00t-ditsoftadd-scout.md` / `gr00t-ditsoftadd-merge.md`；基线摘录：`CURRENT_BASELINE-ditsoftadd.md`。
