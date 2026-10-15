# DitGemm-Shape — denoise 环内 FP8 GemmUniversal (M,N,K) 直方图

- Date: 2026-10-15T12:56:41+08:00
- Status: **measure-only DONE**；**禁 Tune / 禁改 tile / 禁合基线 / 禁改 CURRENT / 禁 commit**
- Stack lock: L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd**
- SoftAdd e2e_full **87.506** / denoise_loop 墙钟 **42.610**
- 本刀未开 SoftAdd pack 新 nsys（GEMM 形状与 L=672 与 SoftAdd 正交；时序以 **Cg4 B1 nsys** 为准）

---

## 0. 一句话结论

**672 发对账 PASS；fp8_gemm ~25.43 ms 中 96.6% 是 M=41「小M税」（qkvo+ff0+ff2），crosskv M=448「大GEMM」仅 3.4%。Tune 优先小 M tile/1SM；crosskv 低 ROI 可缓。**

---

## 1. 方法

| 步 | 做法 |
|---|---|
| A. 静态清单 | `Gr00tN17Config`：`sa_seq=1+40=41`，`vl_seq=448`，`D=32×48=1536`，`ff_inner=4D=6144`，`cross_dim=2048`；32 层交替 self/cross；`CROSS_KV_PRECOMP` 把 16×(to_k+to_v) 提到环外一次 |
| B. Launch 账 | 环内：self 16×6 + cross 16×4 = 160/step ×4 = **640**；+ crosskv 预计算 **32** = **672**（与 B1 nsys L=672 一致） |
| C. 时序 | 读 Thor `cg4_denoise_loop.sqlite`（B1 epic）逐发 `GemmUniversal` duration；按 cutlass **grid(M,N)** 聚类（tile 256×128、cluster 2SM）：`(2,12)`→N=1536 M小；`(2,48)`→N=6144；`(4,12)`→M=448。同 grid 的 K=1536 vs K=6144 用 duration 双峰切分（cut≈52.7 µs，hi 正好 128/loop = ff2） |
| D. SoftAdd | SoftAdd 只融 residual⊕LN_fp8，**不改** FP8 Linear 形状/次数；故 **未** 重采 SoftAdd pack nsys。若架构师要同 session SoftAdd 重采可另批（预期 L 与 shape 同构，ms 噪声级） |

**未改生产路径 / 未改代码 / 未 Tune。**

Artifacts：
- nsys sqlite (Thor): `/home/nvidia/pi05_forge_work/gr00t_fp8_phase_a/b1_denoise_hard_epic/nsys/cg4_denoise_loop.sqlite`
- 旁证: `b1_nsys_cg4_baseline_parse.json` / `b1_cg4_denoise_loop_kern_sum.csv`
- 本刀: `ditgemm_shape_hist.json`（同目录）

---

## 2. 直方图表

| (M,N,K) | L/loop | µs med | ms/loop | % fp8_gemm | % denoise GPU | 家族 | 标签 |
|---|---:|---:|---:|---:|---:|---|---|
| **(41, 1536, 1536)** | **384** | 22.2 | **8.85** | **34.8%** | 19.3% | to_q/k/v/o（self 全 + cross Q/O） | **小M税** |
| **(41, 1536, 6144)** | **128** | 62.6 | **8.21** | **32.3%** | 17.9% | ff.net_2 | **小M税** |
| **(41, 6144, 1536)** | **128** | 57.4 | **7.50** | **29.5%** | 16.4% | ff.net_0 | **小M税** |
| **(448, 1536, 2048)** | **32** | 27.0 | **0.87** | **3.4%** | 1.9% | cross to_k/to_v（环外一次） | 大GEMM |
| **合计** | **672** | — | **25.43** | **100%** | 55.5% | — | — |

核对：L **672=672**；ms **25.43 ≈ B1 fp8_gemm 25.43**（逐发加总 bit 对齐）。

参考：Cg4 denoise GPU **45.788** ms/loop；墙钟 loop Cg4 **43.95** / SoftAdd **42.61**。

### TFLOPS（med，示意）

| shape | ~TFLOPS |
|---|---:|
| (41,1536,1536) | **8.7** |
| (41,1536,6144) | 12.4 |
| (41,6144,1536) | 13.5 |
| (448,1536,2048) | **104** |

→ 同一 256×128×64 2SM 模板：M=41 算力密度极低（小M税）；M=448 已近满血。

---

## 3. Top shapes by time

| # | shape | ms | 备注 |
|---:|---|---:|---|
| 1 | (41,1536,1536) qkvo | 8.85 | 发数最多；单发最短但仍是第一墙（×384） |
| 2 | (41,1536,6144) ff2 | 8.21 | 小M + 胖 K |
| 3 | (41,6144,1536) ff0 | 7.50 | 小M + 胖 N（与 `TVM_FP8_SMALL_M_TILE` / GU-wide 相关） |
| — | (448,…) crosskv | 0.87 | **不是**主墙 |

**小M税合计：24.56 ms = 96.6% of fp8_gemm**  
**大GEMM：0.87 ms = 3.4%**

---

## 4. Tune 优先级建议（本刀不开 Tune）

| 优先 | shape | 理由 |
|---|---|---|
| **P0** | 三个 M=41 | 吃掉 96.6%；tileM=256 对 M=41 浪费；试 1SM / 更小 tileM / `TVM_FP8_SMALL_M_TILE` 档（已有代码旋钮，**本刀未动**） |
| **P3** | M=448 crosskv | 仅 3.4% 且 ~104 TFLOPS；ROI 低 |

**不做：** 未 Shape 就改 so；减步；重开 VisNonV1/V1/L2/AttnScore/DitLayout。

---

## 5. 是否需要 SoftAdd pack 新 nsys？

**默认不需要。** SoftAdd 不合 GEMM；L=672 与四 shape 静态账不变。若要同 session SoftAdd 墙钟对齐的 GEMM µs，可另开一次 measure（预期噪声，不改结论）。

---

## 6. 群可贴摘要

```
DitGemm-Shape DONE（measure only，Cg4 nsys）
672 PASS；fp8_gemm 25.43 ms
Top3: (41,1536,1536) qkvo 8.85 / (41,1536,6144) ff2 8.21 / (41,6144,1536) ff0 7.50
小M税 96.6%；crosskv M=448 仅 3.4%
Tune 优先：小M tile/1SM；勿先啃 crosskv
报告: gr00t-ditgemm-shape.md + ditgemm_shape_hist.json
```
