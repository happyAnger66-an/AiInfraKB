---
id: kb-0000
type: technique
title: 技巧名 + 用在哪
status: draft
claim: 在什么条件下用这个技巧，收益多少，例如「decode 阶段开启后单步延迟从 12ms 降到 9ms」
applies_to:
  hardware: [thor]
  software: {tensorrt: ">=10.8,<11"}
  models: [pi05]
  techniques: [cuda-graph]
evidence:
  - kind: benchmark
    ref: evidence/kb-0000/run.md
    result: {}
verify: 一条能复现收益的命令
confidence: measured
authors: ["agent:<会话或工具名>"]
created: 2026-01-01
last_verified: 2026-01-01
review_by: 2026-04-01   # technique 的 TTL 最短，框架变化快
visibility: private
related: []
---

## 结论

技巧是什么、收益多少、代价是什么。

## 适用条件

什么时候值得用，什么时候没效果或有害。

## 证据

前后对比数据。

## 步骤

可直接照做的操作步骤或代码片段。
