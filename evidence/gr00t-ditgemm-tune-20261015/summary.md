# GR00T DitGemm-Tune — 证据摘要

来源：牛马 `gr00t-ditgemm-tune.md`（2026-10-15 ~13:08 Asia/Shanghai）。SoftAdd pack + env-only A/B（不重编 pack、不改 so）。测完 Verdict = NO-GO。架构师确认 **NO-GO，不合、不 commit、不改 CURRENT**。

## Verdict

| 项 | 值 |
|---|---|
| 决策 | **NO-GO / 不合**（保持 `TVM_FP8_SMALL_M_TILE=1`） |
| 栈 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd** |
| 本 session baseline | `SMALL_M=1` e2e **88.128** / loop **42.764**（锁频同窗；CURRENT e2e_full ~87.5 / 锁值 87.506） |
| 1sm | Δe2e **+0.406**（约 **+0.41**）/ Δloop +0.164；nsys 仍 **672×B2** 256×128×64 **2SM** |
| GU=1 | Δe2e **+0.352**（约 **+0.35**）/ Δloop **+2.141**（约 **+2.14**）；ff0 128 发 → `Gu64x256_1sm` 更慢 |
| 1sm+GU | Δe2e +0.914 / Δloop +2.356 |
| SKIP_2SM | Δe2e +0.454 / Δloop +1.631 |
| auto | Δe2e −0.062（同 mode，会话噪声） |
| legacy=0 | Δe2e +0.109 / Δloop −0.275（噪声带，不构成赢） |
| overall | cos **1.0** / mse **0** / 132/132 **PASS**，bit-identical（tile 不改数值，对速度无意义） |
| Best cand | **无** |

## 一句话

env 档位对 DiT 三个 M=41 要么 `Traits1Sm`（128×256）对 N∈{1536,6144} **can_implement 失败回落 B2**（`1sm` 与基线同核），要么 GU 专档吃到 ff0 `(41,6144,1536)` 但 **Gu64x256_1sm 比现 B2 更慢**（这 128 发约 7.57→8.08 ms；墙钟 loop +2.14，含非 GEMM 副作用）。qkvo / ff2（N=1536）不进 GU 门。**env-only 抠不出小M税。**

## 架构师

**NO-GO 确认。** 保持 SoftAdd + `TVM_FP8_SMALL_M_TILE=1`。不合、不 commit、不改 CURRENT。勿再扫现有 env 指望小M赢；勿 commit Tune cand；勿先啃 crosskv；勿并行硬挖 DitAttnE4（Soft 仍 backlog，见 kb-0013）。勿把本刀写成填上 66.7。

下一拍 **DitGemm-Traits design/scout only**：能 can_implement `(41,1536,*)` / `(41,6144,1536)` 的 1SM Traits，并给 ROI 上界。先不出代码。

全文见同目录 `gr00t-ditgemm-tune.md`。Shape 先验见 `evidence/gr00t-ditgemm-shape-20261015/`（kb-0025）。
