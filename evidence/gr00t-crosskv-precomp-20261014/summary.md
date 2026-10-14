# GR00T cross K/V 环外预计算 — 证据摘要

来源：gr00t优化项目群 2026-10-14；牛马报告 `gr00t-denoise-residual-fuse-report.md`；架构师批合。

## 做法

开关：`MLC_VLA_GR00T_CROSS_KV_PRECOMP`。

将 cross attention 的 K/V 提到 denoise loop 外预计算（独立 pack `..._d1_crosskv_unirt`）。属预计算，非减步。

## 数字（相对 D1 基线路径）

| 指标 | before | after | Δ |
|---|---:|---:|---:|
| denoise_loop | 54.88 ms | 52.91 ms | −1.97 |
| e2e_full | 108.3 ms | 107.5 ms | −0.80 |

精度 vs D1：**bit-identical**。

nsys：cutlass FP8 768→672；quantize −48/loop。

## 备注

- 合入后基线：**L1+D1+crosskv**。
- 与 kb-0005（AdaLN/temb 预计算）同模式：环外不变算子外提。
- 本摘要由群聊出数整理；完整 stages/pack 以牛马报告为准。
