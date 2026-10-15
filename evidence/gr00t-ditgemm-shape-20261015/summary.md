# GR00T DitGemm-Shape — 证据摘要

来源：牛马 `gr00t-ditgemm-shape.md` + `ditgemm_shape_hist.json`（2026-10-15T12:56:41+08:00）。Cg4 pack nsys 逐发 `GemmUniversal` 聚类。**measure-only**：未 Tune、未改 tile、未合基线、未改 CURRENT、未 commit。

## 对账

| 项 | 值 |
|---|---|
| 栈 | L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd** |
| SoftAdd 墙钟 | e2e_full **87.506**；denoise_loop **42.610** |
| 时序源 | Cg4 B1 nsys（SoftAdd 正交，**未重采** SoftAdd pack nsys） |
| 静态账 | 环内 640（self 16×6 + cross 16×4 = 160/step ×4）+ crosskv 预计算 32 = **672** |
| 实测 | L **672=672**；逐发加总 **25.429 ms** ≈ B1 fp8_gemm **25.43**；对账 **PASS** |
| denoise GPU | Cg4 **45.788** ms/loop；fp8_gemm 占 **55.5%** |

SoftAdd 只融 residual⊕LN_fp8，不改 FP8 Linear 形状或次数。JSON 旁注：同 session SoftAdd 的 AdaStatic scout 仍是 L=672 @ 25.93 ms（噪声）。

## 四 shape（ms 为报告四舍五入；JSON 精确值见同目录）

| (M,N,K) | L/loop | ms/loop | % fp8_gemm | 家族 | 标签 |
|---|---:|---:|---:|---|---|
| (41, 1536, 1536) | 384 | **8.85** | 34.8% | to_q/k/v/o | **小M税** |
| (41, 1536, 6144) | 128 | **8.21** | 32.3% | ff.net_2 | **小M税** |
| (41, 6144, 1536) | 128 | **7.50** | 29.5% | ff.net_0 | **小M税** |
| (448, 1536, 2048) | 32 | **0.87** | 3.4% | cross to_k/to_v（环外一次） | 大GEMM |
| 合计 | **672** | **25.43** | 100% | — | — |

小M税合计 **24.56 ms = 96.6%**。crosskv **0.87 ms = 3.4%**。示意 TFLOPS（med）：M=41 约 **8.7 / 12.4 / 13.5**；M=448 约 **104**（同一 256×128×64 2SM 模板，大 GEMM 已近满血）。

## 架构师口径

认 Shape。批 **DitGemm-Tune GO（仅小 M）**，in flight：优先三个 M=41 的 tileM / 1SM / `TVM_FP8_SMALL_M_TILE`（旋钮本刀未动）。crosskv 低 ROI，**禁先啃**。**禁**为这刀改 SoftAdd / QK。未做 Tune A/B，不得 commit、不得合基线。本刀不填 66.7。

全文见同目录 `gr00t-ditgemm-shape.md`；直方图见 `ditgemm_shape_hist.json`。
