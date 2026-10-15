# GR00T AdaStatic merge — 叠入 L1+L3+D1+crosskv+D1take

- Date: 2026-10-15 Asia/Shanghai (~09:50)
- Status: **MERGED**；基线指针已更新；**无 git push**
- Prior scout: `gr00t-adastatic-scout.md`（BANK_STEP=0 isolate，e2e_full −2.62，GO）
- This merge: **AdaStatic + D1take (BANK_STEP=1)** 同包

---

## 合入状态：**DONE**

| 项 | 值 |
|---|---|
| Stack | **L1 + L3 + D1 + crosskv + D1take + AdaStatic** |
| DiT raw | `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_unirt` |
| DiT 新别名（canonical） | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` → 上 |
| 旧 D1take 别名（保留 A/B） | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_unirt` → `..._take_fuse_unirt` |
| bb | `gr00t_n17_bb_fp8_l3_o_down_i4_unirt` |
| CURRENT_BASELINE | `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` 已升本栈 |

Compile env：`ADA_LN_PRECOMP=1` + `CROSS_KV_PRECOMP=1` + `ADA_LN_BANK_STEP=1` + `ADA_LN_STATIC=1` / `--set static_ada_ln_bank=true`。

---

## Sanity（锁频，warmup=8 iters=40；vs D1take-only）

| stage | D1take | **+AdaStatic** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.265 | 19.056 | −0.209 |
| backbone_llm | 19.926 | 19.989 | +0.063 |
| encode_condition | 6.646 | 6.799 | +0.153 |
| denoise_step | 16.261 | 16.501 | +0.240 |
| **denoise_loop** | **51.599** | **49.236** | **−2.362** |
| **e2e_head** | **62.686** | **60.090** | **−2.596** |
| **e2e_full** | **101.519** | **99.347** | **−2.172** |

### Accuracy（denoise_loop，vs D1take pack）

| | value | gate |
|---|---:|---|
| overall cos | **0.99999935** | >0.999 ✅ |
| overall mse | **1.59e-6** | <0.0005 ✅ |
| overall mean_abs | **9.10e-4** | — |
| per-dim pass | **132 / 132**（0–31: 32/32） | ✅ |

完整 per-dim：`adastatic_merge_bench/gate_vs_d1take.json`（亦写入本目录 `adastatic_merge_gate_vs_d1take.json` 副本）。

---

## 建议

e2e_full **~99.3 ms**（≈10.1 Hz）已贴近「~100」档；**建议锁本栈为新速度基线**（`CURRENT_BASELINE.md` 已指向）。距 e2e_full 66.7 仍约 **32+ ms**。

相对 D1take 的增量与 scout 孤立 AdaStatic（−2.62）同量级；与 D1take 正交叠成。

---

## Artifacts

- Report: `/home/nio/shared/gr00t-fp8/gr00t-adastatic-merge.md`
- Thor: `/work/gr00t_fp8_phase_a/adastatic_merge_bench/measure_summary.json`
- Pack: `/work/gr00t_fp8_phase_a/gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_unirt`
- Alias: `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt`
