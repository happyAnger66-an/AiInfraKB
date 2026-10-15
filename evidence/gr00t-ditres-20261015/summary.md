# GR00T DitRes scout — 证据摘要

来源：`gr00t-ditres-scout.md`（2026-10-15）；架构师批 Soft-GO 默认不合。

## Verdict

| | |
|---|---|
| 决策 | **SOFT-GO / 默认不合** → backlog |
| 估 Δe2e_full | **−0.1～−0.5**（修订；inventory 偏乐观） |
| 环内真残留 Linear | **`proj_out_2` ~0.064 ms/loop** |
| quantize 0.41 ms | A2 `to_out` 税 → 另开 attn→e4m3，非本刀 |

## 钉名要点

- 环外 `nvjet_192×8` ~2.05 → AdaStatic
- attn PV wmma/nvjet ≠ proj_out / ≠ QK（AttnScore 对照已证）
- 未改代码、未 smoke（磁盘/与 AdaStatic 抢文件/ROI 不足）

全文见同目录 `gr00t-ditres-scout.md`。
