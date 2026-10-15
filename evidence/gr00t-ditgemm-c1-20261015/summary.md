# GR00T DitGemm-C1 — 证据摘要（Soft-GO + merge）

来源：牛马 `gr00t-ditgemm-c1.md`（2026-10-15T14:20:00+08:00）+ `gr00t-ditgemm-c1-merge.md`（~14:30 Asia/Shanghai）。C1 `Traits1SmM64N128` Soft-GO 后架构师 **GO 合入**（C0 底座同刀）。**已合、已 push、基线已升 +DitGemm-C1。**

## 权威墙钟

| 项 | 值 |
|---|---|
| 决策 | **GO-merged**（Soft-GO 后批合） |
| 权威 e2e_full | **~84.9**（Soft-GO C1 = **84.893**） |
| merge sanity e2e_full | **85.410**（记抖，不压过 84.893） |
| vs C0（同 session） | e2e **87.694→84.893**（**−2.802**）；loop **43.026→39.797**（**−3.229**） |
| vs SoftAdd baseline（同 session Sep22） | e2e **88.255→84.893**（**−3.362**，约 **−3.36**） |
| GEMM nsys vs C0 | **−2.70 ms/loop**（24.059→21.360） |
| 命中 | **640× Traits1SmM64N128（64×128×128/1SM）** + **32× B2**（crosskv） |
| gate | cos **1.0** / mse **0** / 132/132 **bit-identical PASS**（C1 vs C0，以及 merge vs Sep22 SoftAdd） |
| 距 66.7 | **~18 ms** |
| synapsex | `6b7880597ee6b60634c844f98205063527ae48a3`（短 `6b78805`，`feat/silu-mul-fp8`） |

权威墙钟以 Soft-GO C1 **84.893** 为准。merge lockfreq 相对 Sep22 SoftAdd ref 是 88.128→**85.410**（Δ **−2.718**），仍稳赢 SoftAdd ~87.5，但只记抖。

## 栈与运行时

| 项 | 值 |
|---|---|
| Stack | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+DitSoftAdd+**DitGemm-C1** |
| DiT pack | SoftAdd canonical（未改 pack；只升 GEMM so） |
| Runtime | SoftAdd 全套 + **`TVM_FP8_SMALL_M_TILE=1`** + **`LD_PRELOAD=.../libsynapsex_fp8_gemm_c1.so`** |
| Production so | `/work/phase_a_so/libsynapsex_fp8_gemm_c1.so` |
| 代码 | 一刀含 C0 wide-N 1SM dispatch + C1 Traits；仅 `fp8_gemm_sm100.{cuh,cu}` |
| 未动 | crosskv / QK / SoftAdd；未 2-step；未开 DitAttnE4 |

## Microbench（Bias+PerCol；SMALL_M=1；C1 vs C0）

| shape | C0 µs | C1 µs | C1 vs C0 | nsys tile (C1) |
|---|---:|---:|---:|---|
| (41,1536,1536) qkvo | 18.6 | **14.7** | **−21.2%** | **64×128×128/1SM** |
| (41,1536,6144) ff2 | 30.8 | **22.7** | **−26.3%** | 同 |
| (41,6144,1536) ff0 | 28.7 | **22.7** | **−21.1%** | 同 |

C0 对照 tile：128×256×128/1SM。落 ROI 现实带 −2.5～−5 的下沿～中带；乐观 −6～−8 未达。

## 一句话

C1 把小 M 三形从 C0 的 Traits1Sm 128×256 切到 **64×128×128/1SM**（640 发），crosskv 32 发仍 B2。同 session 墙钟 vs C0 e2e **−2.802** / loop **−3.229**，精度 bit-identical。架构师批合；synapsex 一刀含 C0 底座。基线升到 e2e **~84.9**，距 66.7 仍 **~18 ms**。

全文：`gr00t-ditgemm-c1.md` / `gr00t-ditgemm-c1-merge.md`；基线摘录：`CURRENT_BASELINE-ditgemm-c1.md`。C0 单独不合见 kb-0028。
