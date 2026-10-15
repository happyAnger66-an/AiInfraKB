# GR00T Cg4 — 证据摘要（merge + 基线摘录）

来源：牛马 `gr00t-cg4-merge.md` + `CURRENT_BASELINE.md`（2026-10-15 11:20）；架构师批 Cg4 并行合入。denoise `--cuda-graph`，**保持 4 step，禁 2-step**。

## Merge sanity（same-session vs AdaStatic）

| 项 | 值 |
|---|---|
| Stack | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+**Cg4** |
| e2e_full | 96.435 → **90.295**（**−6.140**） |
| denoise_loop | 49.173 → 43.540（**−5.633**） |
| denoise_step | −2.513 |
| overall | cos **1.0** / mse **0.0** bit-identical（132/132） |
| steps | `num_inference_timesteps=4`；compile `"cuda_graph": true` |
| DiT 别名 | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_Cg4_unirt` |
| SHA | `ce568f301076dc20879dad9acdd56a50f4c3237e` |
| Gap | 距 66.7 仍 ~**23.6 ms** |

本 session AdaStatic ref 从锁基线 95.513 抖到 96.435。权威墙钟以 cand **90.295** 为准；刀收益以 same-session Δ 为准。bb 未改。本 pack 为 flag-only `--cuda-graph`（materialize 已进 git，下次重编 bake）。

v4 曾估 Cg4 e2e ~0～−1；实测 loop/e2e 大砍，以本表为准。

全文：`gr00t-cg4-merge.md`；基线指针摘录：`CURRENT_BASELINE.md`。
