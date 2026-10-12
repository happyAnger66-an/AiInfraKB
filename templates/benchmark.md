---
id: kb-0000
type: benchmark
title: 模型 × 硬件 × 配置 的性能基线
status: draft
claim: 核心数字，例如「batch=1 时端到端 11.2ms，其中 attention 占 38%」
applies_to:
  hardware: [thor]
  software: {tensorrt: "10.13"}
  models: [pi05]
  precision: [fp8]
evidence:
  - kind: benchmark
    ref: evidence/kb-0000/run.md
    env: {gpu: thor, clocks: locked}
    result: {latency_ms: 0, throughput: 0}
verify: 跑基线的完整命令
confidence: measured
authors: ["agent:<会话或工具名>"]
created: 2026-01-01
last_verified: 2026-01-01
review_by: 2026-07-01
visibility: private
related: []
---

## 结论

数字和瓶颈结论。

## 适用条件

软件版本、频率、batch、输入形状等全部环境参数。

## 证据

原始数据和测量方法（预热次数、重复次数、取中位数还是均值）。

## 复现

完整命令。
