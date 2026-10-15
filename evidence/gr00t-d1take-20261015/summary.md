# GR00T D1take（AdaLN bank+step）— 证据摘要

来源：`gr00t-d1-take-fuse-report.md`（2026-10-15）；架构师批合。

## 数字

| | base L1+L3+D1+crosskv | +D1take | Δ |
|---|---:|---:|---:|
| e2e_full | 103.247 | 102.033 | **−1.213** |
| e2e_head | 63.723 | 62.339 | −1.385 |
| denoise_loop | 53.001 | 52.952 | −0.049 |
| overall | — | cos1 / mse0 | **bit-identical** |
| take_kernel | 0.462 L=256 | 0.009 L=4 | ≈清掉 |

基线改为 **L1+L3+D1+crosskv+D1take（e2e_full ~102）**。

全文见同目录报告。
