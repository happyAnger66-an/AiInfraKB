---
id: kb-0000            # kb new 分配；手写时取当前最大编号 +1，文件名必须等于 id
type: lesson
title: 一句话说清楚坑和解法
status: draft
claim: 现象 + 数字 + 解法，例如「做法 A 使误差升高 4 倍；改用做法 B 回到基线，延迟多 3%」
applies_to:
  hardware: [thor]
  software: {tensorrt: ">=10.8,<11"}
  models: [pi05]
  techniques: [fp8-quant]
  precision: [fp8]
not_applies_to: 已知不成立的条件，没有就删掉这一行
evidence:
  - kind: benchmark      # benchmark | profile | experiment | source | doc
    ref: evidence/kb-0000/run.md
    env: {gpu: thor}
    result: {}
verify: 一条能复现结论的命令
confidence: measured     # inferred | measured | reproduced
authors: ["agent:<会话或工具名>"]
created: 2026-01-01
last_verified: 2026-01-01
review_by: 2026-07-01   # last_verified + kb.toml 中 lesson 的 TTL
visibility: private      # 只有 public 会发布到博客
related: []
---

## 结论

一段话复述 claim，补充为什么会这样。

## 适用条件

逐条写清前提；不确定的条件写成「未验证」，不要省略。

## 证据

对应 frontmatter 里的 evidence，写清怎么测、测了几次、数字是多少。

## 复现

把 verify 命令展开成步骤。
