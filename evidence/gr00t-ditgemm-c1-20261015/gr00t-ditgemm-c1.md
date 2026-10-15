# DitGemm-C1 — `Traits1SmM64N128`（64×128×128/1SM，门 M≤64）

- Date: 2026-10-15T14:20:00+08:00
- Status: **measure DONE**；**Verdict = Soft-GO**；**默认不合 / 不 commit / 不改 CURRENT**
- Stack lock: L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd**
- SoftAdd CURRENT e2e ~87.5；本 session C0 底座 e2e **87.694** / loop **43.026**；C1 e2e **84.893** / loop **39.797**
- Prior: C0 Soft-GO → 架构师批 C1 GO
- Thor: `pi05-forge-agent` / thor-2239；`FLASHRT_ROOT=/srcs/data/FlashRT`
- so: baseline `/srcs/tvm-relax/build/lib/libtvm_fp8_gemm_unified.so`；C0 `/work/phase_a_so/libsynapsex_fp8_gemm_c0.so`；**C1 `/work/phase_a_so/libsynapsex_fp8_gemm_c1.so`**

---

## 0. 一句话结论

**Soft-GO。** C1 新 Traits `Traits1SmM64N128`（64×128×128/1SM，门 M≤64）在 SoftAdd pack 上 **命中成立**：denoise nsys **640× 64×128×128/1SM + 32× B2(crosskv)**（C0 为 640× Traits1Sm 128×256）。墙钟 same-session vs C0：**e2e −2.802 / loop −3.229**；vs baseline e2e **−3.362**。GEMM nsys **−2.70 ms/loop**。精度 **bit-identical PASS**（cos=1 / mse=0 / 132/132）。Micro 三形 vs C0：**qkvo −21.2% / ff2 −26.3% / ff0 −21.1%**。**默认仍不合**；建议架构师批合（墙钟已稳赢噪声带）。

---

## Verdict

| | |
|---|---|
| **Go / no-go** | **Soft-GO**（命中+墙钟稳赢+gate PASS；默认不合等批） |
| M64N128 命中 | **YES** — 640/672 小M三形走 **64×128×128/1SM** |
| 选中 Traits | **`Traits1SmM64N128`**（非仍 Traits1Sm 128×256） |
| Δe2e_full vs C0 | **−2.802** |
| Δdenoise_loop vs C0 | **−3.229** |
| Δe2e_full vs baseline | **−3.362** |
| ΔGEMM (nsys) vs C0 | **−2.70 ms/loop** |
| overall gate | **PASS** cos=1.0 / mse=0 / 132/132 bit-identical |
| 合基线 / commit / CURRENT | **NO**（本刀默认） |
| 下一步 | **建议批合 C1**（或 C0+C1 一并合）；合前另开 merge 卡 |

---

## 1. 代码 diff 摘要

文件（**未 commit**）：
- `synapsex/operators/fp8_gemm/fp8_gemm_sm100.cuh`：+`Fp8GemmSm100Traits1SmM64N128` = Tile `<_64,_128,_128>` / Cluster `<_1,_1,_1>`
- `synapsex/operators/fp8_gemm/fp8_gemm_sm100.cu`：BiasGelu / Bias / nobias 的 `try_1sm` + trailing ladder + BiasGeluE4m3：**M≤64 优先试 M64N128**，失败再走 C0 链（Traits1Sm→N128→N64→B2）

| 位点 | 改动 |
|---|---|
| 新 Traits | `Traits1SmM64N128` |
| `try_1sm` ×3 | `if (mi <= 64) try M64N128` 置顶 |
| trailing 1SM ladder ×3 + E4m3 | 同门 |
| `SmallMTileMode` 注释 | 文档 C1 行为 |

**未改：** crosskv / QK / SoftAdd / GU 门 / 2-step / Vis*；C0 宽 N 先 try_1sm 底座保留。

工作树：`/work/synapsex_c1/`（Thor）；LT5 `synapsex/operators/fp8_gemm/` 已同步。

---

## 2. Microbench（Bias+PerCol；三形；SMALL_M=1）

| shape | baseline µs | C0 µs | C1 µs | C1 vs C0 | C1 vs base | nsys tile (C1) |
|---|---:|---:|---:|---:|---:|---|
| (41,1536,1536) qkvo | 21.7 | 18.6 | **14.7** | **−21.2%** | −32.4% | **64×128×128/1SM** |
| (41,1536,6144) ff2 | 42.9 | 30.8 | **22.7** | **−26.3%** | −47.1% | 同 |
| (41,6144,1536) ff0 | 41.0 | 28.7 | **22.7** | **−21.1%** | −44.7% | 同 |

C0 对照 tile：128×256×128/1SM；baseline：256×128×64/2SM。

---

## 3. SoftAdd pack same-session A/B（lockfreq；warmup=8 iters=40）

| tag | so | e2e_full | denoise_loop | Δe2e vs C0 | Δloop vs C0 |
|---|---|---:|---:|---:|---:|
| baseline | unified Sep22 | 88.255 | 42.725 | — | — |
| **c0** | synapsex_c0 | **87.694** | **43.026** | 0 | 0 |
| **c1** | synapsex_c1 | **84.893** | **39.797** | **−2.802** | **−3.229** |

其他 stage（C1 vs C0 median ms）：denoise_step −1.208；e2e_head −3.196；vision/llm/enc 噪声级。

### Gate（C1 vs C0）

| | cos | mse | mean_abs | max_abs | per-dim | pass |
|---|---:|---:|---:|---:|---|:---:|
| C1 vs C0 | **1.0** | **0** | **0** | **0** | **132/132** | ✅ |

---

## 4. nsys 命中证明（denoise_loop；12 profiled iters）

| tag | tile / cluster | L/loop | ms/loop | 备注 |
|---|---|---:|---:|---|
| **C0** | Traits1Sm **128×256×128 / 1SM** | **640** | **23.206** | 小M三形 |
| **C0** | B2 256×128×64 / 2SM | **32** | **0.853** | crosskv M=448 |
| **C0 合计** | — | **672** | **24.059** | — |
| **C1** | **M64N128 64×128×128 / 1SM** | **640** | **20.484** | **命中目标核** |
| **C1** | B2 256×128×64 / 2SM | **32** | **0.876** | crosskv 未动 |
| **C1 合计** | — | **672** | **21.360** | ΔGEMM **−2.70** |

→ **小M 三形已切到 64×128×128/1SM**，非仍 Traits1Sm 128×256。crosskv 仍 B2（禁区）。

---

## 5. 解读与建议

| 项 | 判断 |
|---|---|
| C1 是否够？ | **够做 Soft-GO**：命中+墙钟 −2.8 e2e 超噪声；gate 完美 |
| vs ROI 设计 | 现实带 −2.5～−5 命中下沿～中带；乐观 −6～−8 未达 |
| 合入？ | **默认 NO**；**建议架构师批合**（C1 so 或合入 C0+C1 代码） |
| 距 66.7 | SoftAdd~87.5 → C1~84.9，仍约 **18 ms** gap |

---

## 6. 禁区遵守

未动 crosskv / QK / SoftAdd / Softmax / PV；未 2-step；未 VisNonV1/V1/L2/AttnScore/DitLayout；**未合基线 / 未 commit / 未改 CURRENT**；未并行 DitAttnE4；未开 C2 GU。

---

## 7. Artifacts

| | path |
|---|---|
| 本报告 | `/home/nio/shared/gr00t-fp8/gr00t-ditgemm-c1.md` |
| Summary json | `ditgemm_c1_measure_summary.json` |
| Stages / gate / micro / nsys | `ditgemm_c1_artifacts/` |
| Thor bench | `/work/gr00t_fp8_phase_a/ditgemm_c1_bench/` |
| C1 so | `/work/phase_a_so/libsynapsex_fp8_gemm_c1.so` |
| 源码（未 commit） | `synapsex/operators/fp8_gemm/fp8_gemm_sm100.{cuh,cu}`；Thor `/work/synapsex_c1/` |

---

## 8. 群可贴摘要

```
DitGemm-C1 DONE → Soft-GO（默认不合）
命中：640× M64N128(64×128×128/1SM) + 32×B2 crosskv（C0 为 128×256/1SM）
墙钟 vs C0：e2e −2.802 / loop −3.229；vs baseline e2e −3.362
GEMM −2.70 ms/loop；micro qkvo/ff2/ff0 vs C0 −21/−26/−21%
gate bit-identical PASS
建议批合；本刀不合不 commit
报告: gr00t-ditgemm-c1.md
```
