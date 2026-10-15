# Current speed baseline excerpt (GR00T N1.7 FP8) — DitGemm-C1

摘自合入卡 `gr00t-ditgemm-c1-merge.md`（2026-10-15 ~14:30 Asia/Shanghai）。指针文件在 Thor：`/home/nio/shared/gr00t-fp8/CURRENT_BASELINE.md` 与 `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md`。本摘录只记合入时钉住的墙钟、栈和运行时，不补 pack 路径。

- Updated: 2026-10-15 ~14:30 Asia/Shanghai
- Stack: **L1 + L3 + LlmRmsQ + EncFp8 + D1 + crosskv + D1take + AdaStatic + Cg4 + LlmSiluEpi + DitSoftAdd + DitGemm-C1**
- e2e_full 权威: **~84.9**（Soft-GO C1 = **84.893**）
- merge sanity e2e_full: **85.410**（记抖；不压过 Soft-GO **84.893**）
- 距 66.7: **~18 ms**

## Runtime

- DiT pack：SoftAdd canonical（未改 pack；只升 GEMM so）
- 既有 SoftAdd 全套 + **`TVM_FP8_SMALL_M_TILE=1`**
- **`LD_PRELOAD=.../libsynapsex_fp8_gemm_c1.so`**
- Production so：`/work/phase_a_so/libsynapsex_fp8_gemm_c1.so`（`libsynapsex_fp8_gemm_unified.so` / `libtvm_fp8_gemm_unified.so` → C1）
- `/srcs/.../libtvm_fp8_gemm_unified.so`：Sep22 RO 保留；新跑默认 preload phase_a_so C1
- 命中：denoise **640× Traits1SmM64N128（64×128×128/1SM）** + **32× B2** crosskv
- **禁** 未批开 DitAttnE4；**禁** 动 crosskv / QK / SoftAdd；**禁** 丢掉 `SMALL_M_TILE=1`

## Git

- synapsex `feat/silu-mul-fp8` `6b7880597ee6b60634c844f98205063527ae48a3`（短 `6b78805`）
- 一刀 = C0 wide-N 1SM dispatch + C1 `Traits1SmM64N128`
- 仅 `operators/fp8_gemm/fp8_gemm_sm100.{cuh,cu}`

## 权威 vs 抖

| 来源 | e2e_full | 角色 |
|---|---:|---|
| Soft-GO C1（vs C0 same-session） | **84.893** | **权威** |
| merge lockfreq sanity（vs Sep22 SoftAdd ref 88.128） | **85.410** | 抖（Δ −2.718，仍稳赢 ~87.5） |
