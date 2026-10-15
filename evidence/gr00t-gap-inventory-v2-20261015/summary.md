# GR00T 15Hz gap inventory v2 — 证据摘要

来源：牛马 `/home/nio/shared/gr00t-fp8/gr00t-15hz-gap-inventory-v2.md`（2026-10-15）；架构师批 AdaStatic 主刀 + DitRes scout + D1take 落地。

## 基线与缺口

| 项 | 值 |
|---|---|
| 合入基线 | L1+L3+D1+crosskv |
| e2e_full | **~103.5 ms** |
| e2e_head | ~63–64 ms |
| denoise_loop | ~53–55 ms（占 full ~51%） |
| 目标 | e2e_full ≈ 66.7 |
| Gap | **~37 ms** |

Stages（L3 same-session p50）：embed 19.4 / llm 20.2 / encode 6.8 / loop 53.1。

## π0.5 搬迁结论（一句话）

覆盖 + 融合 Q + Ada/cross 预计算 **大半已落地**；可搬合规剩余主要是 **更深预计算（AdaStatic / D1take）** 与 **残留 Linear/epi（DitRes）**。Vision fused 已试过，本轮不 scout。

## 本轮批刀

| ID | 估 Δe2e | 角色 |
|---|---:|---|
| D1take | −0.3～−0.8 | Soft-GO 落地 |
| **AdaStatic** | **−1.5～−3.5** | **主刀**（π0 0034 固定 t bake） |
| DitRes | −0.5～−1.5 | 并行 scout |

乐观 1+2+3 ≈ **3–6 ms** → e2e **~97–100**，仍差 **30+ ms**。

## 明确不要做

steps2/降步；V1 plain；V1b 默认合；L2 QKV；DitLayout 重开；AttnScore；用 e2e_head 冒充 full；路线写成 L1→V1→D1。

全文见同目录 `gr00t-15hz-gap-inventory-v2.md`。
