# GR00T AdaLN / temb 预计算（D1）— 证据摘要

来源：gr00t优化项目群 2026-10-14；牛马报告 `gr00t-d1-residual-gemm-report.md`；架构师批合。

## 做法

开关：`MLC_VLA_GR00T_ADA_LN_PRECOMP`。

将 denoise loop 内相对 timestep 可不变的算子提到循环外：

- `norm1.linear` ×32（AdaLN）
- timestep MLP
- `proj_out_1`

方向：预计算（非减步、非改精度轨）。

## 数字（Thor；相对 phase_ada_ln / L1 合入后基线路径）

| 指标 | before | after | Δ |
|---|---:|---:|---:|
| denoise_loop | 60.9 ms | 56.0 ms | −4.9 |
| e2e_full | 115.5 ms | 109.3 ms | −6.2 |

精度 vs phase_ada_ln：**cos=1 / mse=0 / 132/132 bit-identical**。

pack 名（报告）：`..._phase_ada_ln_d1_precomp_unirt`。

## 备注

- 合入基线当时定为 L1 + D1（+可选 cudagraph@4）；V1 plain 不合。
- 本摘要由群聊出数整理；完整 stages JSON / pack 路径以牛马机上报告为准，晋升前可补抽证据文件。
