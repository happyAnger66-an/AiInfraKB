# GR00T AdaStatic — 证据摘要

来源：scout + merge（2026-10-15）；架构师锁新基线。

## Scout（vs L1+L3+D1+crosskv；BANK_STEP=0）

| stage | base | +AdaStatic | Δ |
|---|---:|---:|---:|
| denoise_loop | 53.670 | 50.316 | **−3.354** |
| e2e_head | 63.322 | 61.332 | −1.990 |
| e2e_full | 103.508 | 100.892 | **−2.615** |

overall cos 0.999999 / mse 1.6e−6；132/132 PASS。

## Merge sanity（叠 +D1take；锁频）

| stage | D1take | +AdaStatic | Δ |
|---|---:|---:|---:|
| denoise_loop | 51.599 | 49.236 | **−2.362** |
| e2e_head | 62.686 | 60.090 | −2.596 |
| e2e_full | 101.519 | **99.347** | **−2.172** |

gate vs D1take：cos 0.999999 / mse 1.6e−6；132/132 PASS。

新基线：**L1+L3+D1+crosskv+D1take+AdaStatic（e2e_full ~99.35）**  
别名：`gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt`

全文见同目录 scout / merge 报告。
