# GR00T D1take（AdaLN bank+step）— 证据摘要

来源：`gr00t-d1-take-fuse-report.md`（落地测）+ `gr00t-d1-take-merge.md`（合入 sanity）；架构师批合。

## 落地测（vs L1+L3+D1+crosskv）

| | base | +D1take | Δ |
|---|---:|---:|---:|
| e2e_full | 103.247 | 102.033 | **−1.213** |
| e2e_head | 63.723 | 62.339 | −1.385 |
| denoise_loop | 53.001 | 52.952 | −0.049 |
| overall | — | cos1 / mse0 | **bit-identical** |
| take_kernel | 0.462 L=256 | 0.009 L=4 | ≈清掉 |

## 合入 sanity（锁频；新基线）

| stage | median ms |
|---|---:|
| denoise_loop | 51.945 |
| e2e_head | 63.370 |
| **e2e_full** | **102.734** |

- DiT 别名：`gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_unirt`
- vs pre-D1take：**bit-identical PASS**
- 指针：`CURRENT_BASELINE.md`（Thor `/work/gr00t_fp8_phase_a/`）

基线锁：**L1+L3+D1+crosskv+D1take（e2e_full ~102.7）**。
