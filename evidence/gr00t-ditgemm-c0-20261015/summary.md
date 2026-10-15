# GR00T DitGemm-C0 — 证据摘要

来源：牛马 `gr00t-ditgemm-c0.md`（2026-10-15T14:01:00+08:00）。C0 dispatch 拓宽 measure（新编 so，**未 commit**）。Verdict = **Soft-GO**。架构师认 **Soft-GO 不合**；C0 工作树/so 留底座；批 **C1 `Traits1SmM64N128` GO in flight**。

## Verdict

| 项 | 值 |
|---|---|
| 决策 | **Soft-GO / 不合**（1SM 命中成立；墙钟未稳赢） |
| 1SM 命中 | **YES** — denoise **640× Traits1Sm(128×256×128/1SM)** + **32× B2**（crosskv）；基线 **672× B2** |
| 选中 Traits | **Traits1Sm 128×256×128 / 1SM**（未落到 N128/N64） |
| 意外 | 新编 so 上 Traits1Sm 已能过（Sep22 旧 so + Tune `1sm` 仍 B2） |
| GEMM | **25.823→24.829** ms/loop（**−0.994**，约 **−0.99**） |
| 墙钟 | e2e **87.680→87.529**（**−0.151**，约 **−0.15**）；loop **44.085→44.152**（**+0.067**，约 **+0.07**） |
| gate | cos **1.0** / mse **0** / 132/132 **bit-identical PASS** |
| 合基线 / commit / CURRENT | **NO** |
| 下一步 | **C1 `Traits1SmM64N128` GO in flight**（64×128×128/1SM，门 M≤64） |
| env | 保持 **`TVM_FP8_SMALL_M_TILE=1`**；勿动 crosskv |
| 栈 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd** |
| 本 session baseline | unified Sep22 e2e **87.680** / loop **44.085**（CURRENT e2e_full ~87.5） |
| C0 so | `/work/phase_a_so/libsynapsex_fp8_gemm_c0.so`（`FP8_CUDA_ARCH=110a`，未 commit） |

## Microbench（Bias+PerCol；SMALL_M=1）

| shape | baseline µs | C0 µs | Δ% | nsys tile |
|---|---:|---:|---:|---|
| (41,1536,1536) qkvo | 21.8 | **18.6** | **−14.5%** | 128×256×128 **1SM**（base 256×128×64 **2SM**） |
| (41,1536,6144) ff2 | 43.0 | **30.8** | **−28.3%** | 同 |
| (41,6144,1536) ff0 | 41.0 | **27.8** | **−32.1%** | 同 |

## 一句话

C0 把 mode=1 宽 N 改成先 `try_1sm` 再 B2 之后，小 M 三形吃上 **Traits1Sm 128×256×128 / 1SM**（640 发），crosskv 32 发仍 B2。GEMM **−0.99 ms/loop**，但 same-session 墙钟 e2e **−0.15** / loop **+0.07** 在噪声带，未稳赢。新编 so 上 Traits1Sm 本身已能过，N128/N64 回落本 session 未触发。精度 bit-identical。**不合**。

## 架构师

**Soft-GO 不合。** 命中成立，墙钟噪声不够合。C0 工作树与实验 so 留底座，不 commit、不改 CURRENT。批 **C1 Traits1SmM64N128 GO in flight**。勿动 crosskv。勿因墙钟噪声合 C0。勿写成已填满 **66.7**。勿丢掉 `TVM_FP8_SMALL_M_TILE=1`。

全文见同目录 `gr00t-ditgemm-c0.md`。Traits design 见 kb-0027；Tune NO-GO 见 kb-0026；Shape 见 kb-0025；SoftAdd 见 kb-0023。
