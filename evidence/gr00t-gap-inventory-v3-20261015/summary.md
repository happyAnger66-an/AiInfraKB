# GR00T 15Hz gap inventory v3 — 证据摘要

来源：牛马 `/home/nio/shared/gr00t-fp8/gr00t-15hz-gap-inventory-v3.md`（2026-10-15）；架构师批 **VisNonV1 主 scout** + 并行 **DitAttnE4**；**LlmRmsQ** 排其后（禁重放 L2）。

## 基线与缺口

| 项 | 值 |
|---|---|
| 合入基线 | L1+L3+D1+crosskv+D1take+AdaStatic |
| e2e_full | **~99.35 ms** |
| e2e_head | ~60.09 ms |
| denoise_loop | ~49.24 ms（占 full ~50%） |
| 目标 | e2e_full ≈ 66.7 |
| Gap | **~32.6 ms** |

Stages（新锁）：embed 19.1 / llm 20.0 / encode 6.8 / loop 49.2。

## 相对 v2

已合 D1take（−1.21）+ AdaStatic（叠 −2.17）；DitRes Soft-GO 默认不合；π0 预计算主菜单基本吃完；gap 37→32.6。

## 本轮批刀

| ID | 估 Δe2e | 角色 |
|---|---:|---|
| **VisNonV1**（ViT attn FP8） | −2～−5? | **主 scout**（非 V1 plain） |
| **DitAttnE4** | −0.5～−2? | **并行**（attn→e4m3；非 AttnScore） |
| **LlmRmsQ** | −0.5～−2? | **其后**（禁重放 L2） |

三刀叠完乐观几～十几 ms → 仍冲不满 66.7。

## 明确不要做

steps2/降步；V1/V1b 默认合；L2 QKV；DitLayout；AttnScore；DitRes 当主刀；用 e2e_head 冒充 full；重放已合 AdaStatic/D1take。

全文见同目录 `gr00t-15hz-gap-inventory-v3.md`。
