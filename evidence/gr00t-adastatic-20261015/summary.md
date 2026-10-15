# GR00T AdaStatic — 证据摘要

来源：`gr00t-adastatic-scout.md`（2026-10-15）；架构师批合（叠 +D1take）。

## 测数（vs L1+L3+D1+crosskv；BANK_STEP=0）

| stage | base | +AdaStatic | Δ |
|---|---:|---:|---:|
| denoise_loop | 53.670 | 50.316 | **−3.354** |
| e2e_head | 63.322 | 61.332 | −1.990 |
| e2e_full | 103.508 | 100.892 | **−2.615** |

- overall cos **0.999999** / mse **1.6e−6**；per-dim **132/132** PASS
- pack params 1305→1370（+65 static 表）
- 合入：叠到 **+D1take ~102.7**；叠后 sanity 待报

全文见同目录报告。
