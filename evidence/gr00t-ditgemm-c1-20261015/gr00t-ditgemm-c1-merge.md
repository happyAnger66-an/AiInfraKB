# GR00T DitGemm-C1 merge — `Traits1SmM64N128` + C0 wide-N 1SM dispatch

- Date: 2026-10-15 ~14:30 Asia/Shanghai
- Status: **MERGED**；基线指针已更新；**已 push**（见 Commit）
- Prior: C0 Soft-GO → C1 Soft-GO → 架构师 **GO 合入**（C0 底座同刀）
- Soft: `gr00t-ditgemm-c1.md`；**DitAttnE4 Soft 仍 backlog**；**禁** crosskv / QK / SoftAdd 逻辑 / 2-step

---

## 合入状态：**DONE**

| 项 | 值 |
|---|---|
| Stack | **L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+DitSoftAdd+DitGemm-C1** |
| DiT pack | SoftAdd canonical（未改 pack；只升 GEMM so） |
| Production so | `/work/phase_a_so/libsynapsex_fp8_gemm_c1.so`（`libsynapsex_fp8_gemm_unified.so` / `libtvm_fp8_gemm_unified.so` → C1） |
| `/srcs/.../libtvm_fp8_gemm_unified.so` | Sep22 RO 保留；新跑默认 `LD_PRELOAD` phase_a_so C1 |
| CURRENT_BASELINE | `/home/nio/shared/gr00t-fp8/CURRENT_BASELINE.md` + `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` |
| e2e 权威 | **~84.9**（Soft-GO C1 = **84.893**）；merge sanity **85.410** |
| 距 66.7 | **~18 ms** |

Runtime：既有 SoftAdd 全套 + **`TVM_FP8_SMALL_M_TILE=1`** + **`LD_PRELOAD=.../libsynapsex_fp8_gemm_c1.so`**。

---

## Sanity

### Soft-GO C1（权威；vs C0 same-session）

| | C0 | **C1** | Δ |
|---|---:|---:|---:|
| denoise_loop | 43.026 | **39.797** | **−3.229** |
| **e2e_full** | 87.694 | **84.893** | **−2.802** |

Gate C1 vs C0：cos=1 / mse=0 / **132/132** bit-identical，PASS。
nsys：640× **64×128×128/1SM** + 32×B2 crosskv；GEMM −2.70 ms/loop。

### Merge lockfreq（vs Sep22 SoftAdd ref；升 so 后）

| stage | ref | **cand C1** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.129 | 18.806 | −0.323 |
| backbone_llm | 17.425 | 17.407 | −0.018 |
| encode_condition | 5.249 | 5.141 | −0.108 |
| denoise_step | 13.764 | 12.889 | −0.875 |
| **denoise_loop** | 44.981 | **40.210** | **−4.772** |
| e2e_head | 52.361 | 48.309 | −4.052 |
| **e2e_full** | 88.128 | **85.410** | **−2.718** |

Gate vs Sep22 SoftAdd：cos=1.0 / mse=0 / mean_abs=0 / **132/132**，PASS。

> 权威墙钟以 Soft-GO C1 **84.893** 为准（架构师钉 ~84.9）；merge session 抖到 85.410，仍稳赢 SoftAdd~87.5。

---

## Git commit

| repo | branch | SHA | message（首行） | push |
|---|---|---|---|---|
| `synapsex` | `feat/silu-mul-fp8` | `6b7880597ee6b60634c844f98205063527ae48a3` | `feat(fp8_gemm): DitGemm-C1 Traits1SmM64N128 + C0 wide-N 1SM dispatch` | **已 push** → `origin`（gitlab） |

### Files

**synapsex**（原子一刀 = C0 底座 + C1 Traits）
- `operators/fp8_gemm/fp8_gemm_sm100.cuh`：+`Fp8GemmSm100Traits1SmM64N128`（64×128×128/1SM）
- `operators/fp8_gemm/fp8_gemm_sm100.cu`：M≤64 优先 M64N128；宽 N 先 try_1sm（Traits1Sm→N128→N64）再 B2

未动 crosskv / QK / SoftAdd；未 2-step；未开 DitAttnE4；未碰 GitHub。

---

## Artifacts

- Merge card: `/home/nio/shared/gr00t-fp8/gr00t-ditgemm-c1-merge.md`
- Soft report: `/home/nio/shared/gr00t-fp8/gr00t-ditgemm-c1.md`
- Thor merge bench: `/work/gr00t_fp8_phase_a/ditgemm_c1_merge_bench/`（`MERGE_PASS.flag`）
- C1 so: `/work/phase_a_so/libsynapsex_fp8_gemm_c1.so`
- Elevate stamp: `/work/phase_a_so/DITGEMM_C1_SO_ELEVATED.txt`

## 建议

DitGemm-C1 **已合**；e2e_full **~84.9 ms**；距 66.7 仍 ~18 ms。下一刀：**DitAttnE4 Soft**（backlog）或其他 denoise 刀；禁再挖 C2 GU 除非架构师另批。
