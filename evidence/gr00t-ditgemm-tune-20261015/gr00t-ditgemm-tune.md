# DitGemm-Tune — 小 M=41 env A/B（1SM / tile / GU）

- Date: 2026-10-15 ~13:08 Asia/Shanghai
- Status: **measure DONE**；**Verdict = NO-GO**；**默认不合 / 不 commit / 不改 CURRENT**
- Stack lock: L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd**
- SoftAdd CURRENT e2e_full **~87.5**；本 session baseline e2e **88.128** / loop **42.764**（锁频同窗）
- Prior: `gr00t-ditgemm-shape.md`（小M税 96.6%）
- Thor: `pi05-forge-agent` / thor-2239；`FLASHRT_ROOT=/srcs/data/FlashRT`
- so: `/srcs/tvm-relax/build/lib/libtvm_fp8_gemm_unified.so`（LD_PRELOAD；含 `TVM_FP8_SMALL_M_TILE` / `GU_TILE` / `SKIP_2SM`）

---

## 0. 一句话结论

**NO-GO。** 现 SoftAdd env（`TVM_FP8_SMALL_M_TILE=1`）已是本刀最优；`1sm` 对 N∈{1536,6144} **can_implement 失败回落 B2**（与基线同核）；`GU_TILE` 吃到 ff0 但 **Gu64x256_1sm 比 B2 慢**（loop +2.1 ms）。精度全 PASS（bit-identical）。**不合基线、不 commit、不改 CURRENT。**

---

## Verdict

| | |
|---|---|
| **Go / no-go** | **NO-GO**（默认不合；等架构师批） |
| Best cand | **无**（保持 baseline env） |
| 推荐 env | **`TVM_FP8_SMALL_M_TILE=1`**（SoftAdd 现网不动） |
| Speed | 全 cand Δe2e ≥ −0.06（噪声）或回退 |
| overall gate | **PASS** cos=1.0 / mse=0 / 132/132（各 cand vs SoftAdd baseline env） |
| nsys | `1sm` 仍 672×B2；`GU` 128×Gu64x256 替换 ff0 但更慢 |

---

## 1. 方法

| 步 | 做法 |
|---|---|
| Pack | SoftAdd DiT + SiluMul bb；**不重编 pack / 不改 so** |
| Baseline | `TVM_FP8_SMALL_M_TILE=1`（SoftAdd merge 现 env） |
| Cand A | `SMALL_M_TILE=auto`（≡ mode 1） |
| Cand B | `SMALL_M_TILE=1sm`（强制先 try_1sm） |
| Cand C | `1`+`GU_TILE=1`；`1sm`+`GU`；`1`+`SKIP_2SM_SMALL_M=1` |
| Neg | `SMALL_M_TILE=0`（legacy B2-first） |
| Timing | same-session lockfreq；warmup=8 iters=40；gpc=1575 / nvd=1692 GATE PASS |
| Gate | 同 SoftAdd pack、各 cand env 子进程 dump `denoise_loop` actions vs baseline env |
| nsys | baseline / cand_b_1sm / cand_c_gu；denoise_loop 3+12；分桶 GemmUniversal |

**禁区遵守：** 未动 crosskv / QK / SoftAdd / Softmax / PV；未 2-step；未 VisNonV1/V1；**未合入 / 未 commit / 未改 CURRENT_BASELINE.md**。

---

## 2. Timing（lockfreq same-session）

| tag | env | e2e | loop | Δe2e | Δloop | gate |
|---|---|---:|---:|---:|---:|:---:|
| **baseline** | `SMALL_M=1` | **88.128** | **42.764** | 0 | 0 | ✅ |
| cand_a_auto | `auto` | 88.065 | 42.760 | **−0.062** | −0.003 | ✅ |
| cand_b_1sm | `1sm` | 88.534 | 42.928 | **+0.406** | +0.164 | ✅ |
| cand_c_gu | `1`+`GU=1` | 88.480 | 44.905 | +0.352 | **+2.141** | ✅ |
| cand_c_1sm_gu | `1sm`+`GU` | 89.042 | 45.120 | +0.914 | +2.356 | ✅ |
| cand_c_skip2sm | `1`+`SKIP_2SM` | 88.581 | 44.395 | +0.454 | +1.631 | ✅ |
| neg_legacy | `0` | 88.237 | 42.488 | +0.109 | −0.275 | ✅ |

> cand_a Δe2e −0.062：同 mode，记会话噪声。neg_legacy loop −0.275 / e2e +0.109：噪声带，不构成赢。

### Accuracy（overall 门 cos>0.999 ∧ mse<0.0005）

| cand | cos | mse | per-dim | pass |
|---|---:|---:|---|:---:|
| all cands vs baseline env | **1.0** | **0** | **132/132** | ✅ |

Tile 路径切换不改 SoftAdd pack 数值（bit-identical）。

---

## 3. nsys A/B（denoise_loop；12 profiled iters）

| tag | GemmUniversal | L/iter | ms/iter | tile / cluster |
|---|---|---:|---:|---|
| **baseline** | B2 only | **672** | **25.766** | 256×128×64 / **2SM** |
| **cand_b_1sm** | B2 only | **672** | 25.160 | **同核** 256×128×64 / **2SM**（1sm 未吃上） |
| **cand_c_gu** | B2 + GU | 544 + **128** | 18.201 + **8.076** = **26.277** | B2 同；GU = **64×256×128 / 1SM** |

### 解读

1. **`1sm` 无效：** kern 名仍是 `SM100_MMA_F8F6F4_2x1SM` + tile 256×128 + cluster 2×1。对 N∈{1536,6144}，`Traits1Sm`（128×256）**can_implement 失败** → 回落 B2，与 baseline 同构。墙钟 ±0.2～0.4 为噪声/会话抖。
2. **`GU_TILE` 有效但更慢：** ff0 `(41,6144,1536)` 128 发切到 `Gu64x256_1sm`（IsGuFp8Shape: M≤64 ∧ N≥4096）。原 B2 上这 128 发 ≈7.57 ms，GU 后 **8.08 ms**（med 62 µs）；墙钟 loop **+2.14 ms**（含非 GEMM 副作用）。
3. **qkvo / ff2（N=1536）** 不进 GU 门；`1sm` 也吃不到 → 小M税主体未被动。

---

## 4. 失败根因（一句话）

**env 档位对 DiT 三形要么 can_implement 失败回落 B2（1sm），要么 GU 专档比现 B2 更慢；env-only 抠不出小M税。**

---

## 5. 建议（等架构师批；本刀不合）

| 项 | 建议 |
|---|---|
| 合入 | **NO** — 保持 SoftAdd + `TVM_FP8_SMALL_M_TILE=1` |
| 下一步（若继续 DitGemm） | 需 **新 1SM Traits** 能 can_implement `(41,1536,*)` / `(41,6144,1536)`（或调 tileM/N/K），再 microbench；**非**再扫现有 env |
| 不做 | 勿抬 `CUTLASS_MIN_M`；勿动 crosskv；勿重开 SoftAdd/QK/PV |

---

## 6. Artifacts

| | path |
|---|---|
| Report | `/home/nio/shared/gr00t-fp8/gr00t-ditgemm-tune.md` |
| Summary json | `ditgemm_tune_measure_summary.json` |
| Thor bench | `/work/gr00t_fp8_phase_a/ditgemm_tune_bench/` |
| Stages / gate / nsys | `stages_*.json` / `gate_per_cand.json` / `nsys/{baseline,cand_b_1sm,cand_c_gu}_denoise_loop.*` |
| Shape prior | `gr00t-ditgemm-shape.md` + `ditgemm_shape_hist.json` |

---

## 7. 群可贴摘要

```
DitGemm-Tune DONE → NO-GO（不合）
SoftAdd pack + env-only；gate 全 PASS bit-identical
baseline(SMALL_M=1) e2e 88.128 / loop 42.764
1sm: 仍 672×B2（can_implement 失败）Δe2e +0.41
GU: ff0→Gu64x256 但更慢 Δloop +2.14
SKIP_2SM / legacy: 无赢
推荐：保持 TVM_FP8_SMALL_M_TILE=1；小M税要新 1SM Traits 非现 env
报告: gr00t-ditgemm-tune.md
```
