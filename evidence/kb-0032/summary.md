# kb-0032 evidence summary — UniRT+ApexInfer gr00t_n17 P0–P4

Date: 2026-10-15 (Asia/Shanghai)
Source: 牛马 Thor 报告 + 架构师批合（gr00t优化项目群）；合入卡 `gr00t-apex-merge.md`

## Merge

| 项 | 值 |
|---|---|
| repo | apexinfer |
| tip | **ec7669e** (master, `--no-ff` Merge `feat/gr00t-n17-pipeline`) |
| feat tip | c71d313（含 glue；合前） |
| 内容 | `gr00t_n17` 双 Executor + host glue + `model_dir_dit`；CONTRACT 写明 Session 墙钟 ≠ lockfreq e2e |

## Precision

| gate | cos | mse | note |
|---|---:|---:|---|
| P3 denoise vs PT | 0.99999721 | 7.14e-6 | Apex↔UniRT denoise bit-identical |
| host glue 真输入 | 0.999808 | 0.000482 | business≡stage bit-identical；mRoPE `_qwen3vl_text_mrope` |

Standing gate: cos>0.999 ∧ mse<0.0005 — both PASS.

## Timing (lockfreq, same machine, warmup=8 / iters=40)

| stage | forge | Apex | Δ |
|---|---:|---:|---:|
| denoise | 39.45 | 42.16 | +2.70 |
| e2e_full | 83.70 | stage 83.02 / business 83.94 | −0.68 / +0.24 |

host glue (PT capture) ~1104 ms 环外，未计入 Apex e2e。

## CONTRACT checklist

- [x] 双包双 Executor（bb+dit `*_unirt`）
- [x] glue in pipeline（不进图）
- [x] 无合并包 / 无 pi05 塞入 / 无 RTC 分叉
- [x] 有 function_io → 不必 register_arch
- [x] Session 墙钟 ≠ lockfreq e2e 已文档化
- [x] FP8 Soft 仍冻结

## Reports (Thor)

`/home/nio/shared/gr00t-fp8/gr00t-apex-p0-pack-scout.md`
`/home/nio/shared/gr00t-fp8/gr00t-apex-p1-unirt-smoke.md`
`/home/nio/shared/gr00t-fp8/gr00t-apex-p2-pipeline.md`
`/home/nio/shared/gr00t-fp8/gr00t-apex-p3-gate.md`
`/home/nio/shared/gr00t-fp8/gr00t-apex-glue.md`
`/home/nio/shared/gr00t-fp8/gr00t-apex-p4-timing.md`
`/home/nio/shared/gr00t-fp8/gr00t-apex-merge.md`
