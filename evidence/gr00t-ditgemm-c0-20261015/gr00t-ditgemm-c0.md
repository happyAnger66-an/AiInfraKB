# DitGemm-C0 — dispatch 拓宽（Traits1Sm → N128→N64；宽 N 先 1SM）

- Date: 2026-10-15T14:01:00+08:00
- Status: **measure DONE**；**Verdict = Soft-GO**；**默认不合 / 不 commit / 不改 CURRENT**
- Stack lock: L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd**
- SoftAdd CURRENT e2e ~87.5；本 session baseline e2e **87.680** / loop **44.085**
- Prior: Traits design Soft-GO → 架构师批 C0 GO
- Thor: `pi05-forge-agent` / thor-2239；`FLASHRT_ROOT=/srcs/data/FlashRT`
- so: baseline `/srcs/tvm-relax/build/lib/libtvm_fp8_gemm_unified.so`（Sep22）；C0 `/work/phase_a_so/libsynapsex_fp8_gemm_c0.so`（本刀新编，`FP8_CUDA_ARCH=110a`）

---

## 0. 一句话结论

**Soft-GO。** C0 让 SoftAdd pack 宽 N 小 M **吃上 1SM**：denoise nsys **640× Traits1Sm(128×256×128/1SM) + 32× B2(crosskv)**（基线 672× B2）；fp8_gemm **−0.99 ms/loop**。墙钟 e2e **−0.15** / loop **+0.07**（噪声带，未稳定兑现）。精度 **bit-identical PASS**。意外：新编 so 上 **Traits1Sm 本身 can_implement 成功**（未落到 N128/N64）；C0 关键仍是 **mode=1 宽 N 先 try_1sm 再 B2**（否则 B2 先成功永吃不到）。**默认不合**；建议开 **C1 M64N128** 继续抠 M 拟合，或加长 A/B 确认墙钟。

---

## Verdict

| | |
|---|---|
| **Go / no-go** | **Soft-GO**（命中成立；墙钟未稳赢；默认不合等批） |
| 1SM 命中 | **YES** — 640/672 = 小M三形；crosskv 32 仍 B2 |
| 选中 Traits | **Traits1Sm 128×256×128 / 1SM**（非 N128/N64） |
| Δe2e_full | **−0.151**（噪声） |
| Δdenoise_loop | **+0.067**（噪声） |
| ΔGEMM (nsys) | **−0.994 ms/loop** |
| overall gate | **PASS** cos=1.0 / mse=0 / 132/132 bit-identical |
| 合基线 / commit / CURRENT | **NO**（本刀默认） |
| 下一步 | **建议开 C1**（`Traits1SmM64N128`）；C0 可留实验 so |

---

## 1. 代码 diff 摘要

文件：`synapsex/operators/fp8_gemm/fp8_gemm_sm100.cu`（+93/−20；**未 commit**）

| 位点 | 改动 |
|---|---|
| `try_1sm` ×3（BiasGelu / Bias / nobias） | 宽 N：`Traits1Sm` 失败后继续 **N128→N64**；全失败 `return false` |
| mode=1 宽 N `else` ×3 | **先 `try_1sm` 再 `try_b2`**（0021：勿先 B2 吃死 1SM） |
| trailing 1SM ladder ×3 + BiasGeluE4m3 | 同宽 N N128→N64 回落 |
| `SmallMTileMode` 注释 | 文档 mode=1 现行为 |

**未改：** crosskv / QK / SoftAdd / GU 门 / 2-step / Vis*；**未** 新 Traits struct（C1 未开）。

本地 bak：`fp8_gemm_sm100.cu.c0bak`。工作树可留。

---

## 2. Microbench（Bias+PerCol；三形；SMALL_M=1）

| shape | baseline µs | C0 µs | Δ% | nsys tile |
|---|---:|---:|---:|---|
| (41,1536,1536) qkvo | 21.8 | **18.6** | **−14.5%** | C0: 128×256×128 **1SM**；base: 256×128×64 **2SM** |
| (41,1536,6144) ff2 | 43.0 | **30.8** | **−28.3%** | 同 |
| (41,6144,1536) ff0 | 41.0 | **27.8** | **−32.1%** | 同 |

`1sm` env 下 C0 同形（qkvo 17.7 / ff2 30.8 / ff0 28.7）；baseline+1sm 仍 B2 量级（旧 so Traits1Sm 路径失败行为）。

---

## 3. SoftAdd pack same-session A/B（lockfreq）

| tag | so | e2e_full | denoise_loop | Δe2e | Δloop |
|---|---|---:|---:|---:|---:|
| **baseline** | unified Sep22 | **87.680** | **44.085** | 0 | 0 |
| **c0** | synapsex_c0 | **87.529** | **44.152** | **−0.151** | **+0.067** |

其他 stage（median ms）：denoise_step −0.286；e2e_head −1.174；vision/llm/enc 噪声级。

### Gate

| | cos | mse | mean_abs | max_abs | per-dim | pass |
|---|---:|---:|---:|---:|---|:---:|
| C0 vs baseline so | **1.0** | **0** | **0** | **0** | **132/132** | ✅ |

---

## 4. nsys 命中证明（denoise_loop；12 profiled iters）

| tag | tile / cluster | L/loop | ms/loop | 备注 |
|---|---|---:|---:|---|
| **baseline** | B2 **256×128×64 / 2SM** | **672** | **25.823** | 全 B2 |
| **C0** | **Traits1Sm 128×256×128 / 1SM** | **640** | **23.958** | 小M三形 |
| **C0** | B2 256×128×64 / 2SM | **32** | **0.871** | crosskv M=448 |
| **C0 合计** | — | **672** | **24.829** | ΔGEMM **−0.994** |

→ **宽 N 已走 1SM**（Traits1Sm），非仍全 B2。N128/N64 回落本 session **未触发**（Traits1Sm 已成功）。

> 与 Traits design「Traits1Sm 对 DiT 宽 N 软失败」不完全一致：**Sep22 旧 so + Tune 1sm 仍 B2**；**本刀新编 so 上 Traits1Sm 可 initialize**。C0 的 mode=1 宽 N 先 1SM 是生产路径吃上的必要条件。

---

## 5. 解读与建议

| 项 | 判断 |
|---|---|
| C0 是否够？ | **部分够**：命中+GEMM −1ms；墙钟未稳赢到「可合」门槛 |
| 为何墙钟没吃满 GEMM Δ？ | Cg4 图内/CPU/噪声；loop 甚至 +0.07；需更长 A/B 或同窗多轮 |
| 是否开 C1？ | **建议 YES** — TileM=128 对 M=41 仍浪费 ~68%；`M64N128` 可能再抠 |
| 合入？ | **NO**（默认）；若架构师要先合 C0 探路，需另批 + 更稳墙钟 |

---

## 6. 禁区遵守

未动 crosskv / QK / SoftAdd / Softmax / PV；未 2-step；未 VisNonV1/V1/L2/AttnScore/DitLayout；**未合基线 / 未 commit / 未改 CURRENT**；未并行 DitAttnE4；未开 C1 代码。

---

## 7. Artifacts

| | path |
|---|---|
| 本报告 | `/home/nio/shared/gr00t-fp8/gr00t-ditgemm-c0.md` |
| Summary json | `ditgemm_c0_measure_summary.json` |
| Stages / gate / micro | `ditgemm_c0_artifacts/` |
| Thor bench | `/work/gr00t_fp8_phase_a/ditgemm_c0_bench/` |
| C0 so | `/work/phase_a_so/libsynapsex_fp8_gemm_c0.so` |
| 源码（未 commit） | `synapsex/operators/fp8_gemm/fp8_gemm_sm100.cu` |

---

## 8. 群可贴摘要

```
DitGemm-C0 DONE → Soft-GO（默认不合）
命中：640× Traits1Sm(128×256/1SM) + 32×B2 crosskv（基线 672×B2）
GEMM −0.99 ms/loop；墙钟 e2e −0.15 / loop +0.07（噪声）；gate bit-identical PASS
意外：新 so 上 Traits1Sm 已能过；C0 关键=宽N先 try_1sm
建议开 C1 M64N128；本刀不合不 commit
报告: gr00t-ditgemm-c0.md
```
