# GR00T DitGemm-Traits — 证据摘要

来源：牛马 `gr00t-ditgemm-traits-design.md`（2026-10-15T13:20:00+08:00）。design/scout only（不出代码、不编 so、不合基线、不改 CURRENT）。Verdict = **Soft-GO**。架构师批实现序：先 **C0** dispatch，不够再 **C1**。

## Verdict

| 项 | 值 |
|---|---|
| 决策 | **Soft-GO / 默认不合**（值得开一刀实现+measure；非必赢） |
| 本刀 | design/scout；**禁出代码** |
| 栈 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd** |
| 基线 | SoftAdd e2e_full **~87.5**；距 **66.7** 仍约 **20.8 ms** |
| 根因 | `Traits1Sm`(128×256×128/1SM) 对 DiT 宽 N 软失败回落 B2；`try_1sm` 对 N>1024 **只试** Traits1Sm，不回落 N128/N64 |
| Gu64 | 能过但 ff0 更慢（128 发 +0.51 ms / loop **+2.14**）→ **C2 Soft-NO** |
| 首刀 | **C0** dispatch 拓宽：宽 N 试 `Traits1SmN128`→`N64`（零新 struct）microbench 三形 |
| 次刀 | 不够再 **C1** `Traits1SmM64N128`=64×128×128/1SM，门 **M≤64** |
| ROI 乐观 | Δe2e **−6～−8.5**（仍留 gap ~12–15） |
| ROI 现实 | Δe2e **−2.5～−5** |
| ROI 悲观 | **≥0**（能过但如 Gu64 回归）→ NO-GO 不合 |
| env | 保持 **`TVM_FP8_SMALL_M_TILE=1`** |
| DitAttnE4 | Soft **backlog**；勿并行硬啃 |

## 一句话

`try_1sm` 对 N>1024 只打 `Traits1Sm`(128×256×128/1SM)，该档在 PerColBias 下对 DiT 宽 N（1536/6144）软失败回落 B2，且不回落已编译的 N128/N64。同形 Gu64（TileM=64）能过但 ff0 更慢，故 C2 默认 Soft-NO。下一实现刀先 C0（只改分派）microbench 三形；不够再 C1 新 Traits。ROI 吃不完 gap ~20.8。默认仍不合，等测完再批。

## 架构师

**Soft-GO。** 实现序：① C0 dispatch（N128→N64→Traits1Sm→B2）microbench 三形；② 不够再 C1 `Traits1SmM64N128`。C3 仅 C1 不足时的宽 N 备选；C2/C4 默认不做。保持 `TVM_FP8_SMALL_M_TILE=1`。本刀不出代码；下一实现刀默认仍不合、不 commit、不改 CURRENT。勿并行硬啃 DitAttnE4 Soft。

全文见同目录 `gr00t-ditgemm-traits-design.md`。Shape 见 kb-0025；Tune NO-GO 见 kb-0026。
