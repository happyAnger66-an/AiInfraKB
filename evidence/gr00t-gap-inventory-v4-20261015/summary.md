# GR00T 15Hz gap inventory v4 — 证据摘要

来源：牛马 `gr00t-15hz-gap-inventory-v4.md`（2026-10-15 ~11:05）；**measure/inventory only**，不改代码。写于 **Cg4 合入之前**；Cg4 实测见 kb-0019，不要用本表覆盖。

## 基线与缺口

| 项 | 值 |
|---|---|
| 合入基线 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic |
| e2e_full | **95.513 ms** |
| e2e_head | 58.667 ms（head 已过 15 Hz） |
| denoise_loop | **49.714 ms**（约占 full 一半，52%） |
| 目标 | e2e_full ≈ 66.7 |
| Gap | **~28.8 ms** |

Stages：embed 19.083 / llm 18.568 / encode 5.177 / loop 49.714。

## 相对 v3

已合 LlmRmsQ（merge e2e −1.75）+ EncFp8（encode −1.44；merge e2e −2.73 vs LlmRmsQ session）。π0 预计算与 bb RmsQ/Enc **已吃完**。VisNonV1 NO-GO；DitAttnE4 / DitRes Soft-GO 默认不合。gap 32.6→28.8。

## 剩余合规刀（当时估，未证实）

| 组合 | 估合计 | 落地后 e2e |
|---|---:|---:|
| DitSoftAdd + DitAttnE4 Soft + DitRes + Cg4 | ~0.6～3.1 | ~92～95 |
| 再加核债 / Vision Soft / DitGemm 乐观 | 仍差 15–25+ ms | 冲不满 66.7 |

v4 对 Cg4 的 e2e 估是 **~0～−1**（loop 曾更大）。合入实测以 kb-0019 为准。

## 明确不要做

steps2/降步；V1 / VisNonV1；L2 QKV；DitLayout；AttnScore；DitAttnE4 / DitRes 当主刀；挖 state_encoder / vlln；用 e2e_head 冒充 full。

全文见同目录 `gr00t-15hz-gap-inventory-v4.md`。
