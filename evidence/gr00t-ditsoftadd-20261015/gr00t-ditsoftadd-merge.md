# GR00T DitSoftAdd merge — FlashRT `res_ln_fp8` glue（denoise residual⊕LN→e4m3）

- Date: 2026-10-15 ~12:45 Asia/Shanghai
- Status: **MERGED**；基线指针已更新；**已 push**（见 Commit）
- Prior: Soft scout「无核」过时 → B1 epic 钉 `flashrt.res_ln_fp8` → 架构师升 **GO glue**
- Epic: `gr00t-b1-denoise-hard-epic.md`；**DitGemm 本轮不挖**；**禁** QK/softmax/PV

---

## 合入状态：**DONE**

| 项 | 值 |
|---|---|
| Stack | **L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+DitSoftAdd** |
| DiT (canonical) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` → `..._cg4_softadd_unirt` |
| DiT (raw) | `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_cg4_softadd_unirt` |
| DiT (pre-SoftAdd) | `..._Cg4_pre_SoftAdd_unirt` → `..._adastatic_cg4_unirt` |
| bb (unchanged SiluMul) | `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_silumul_i4_unirt` |
| CURRENT_BASELINE | `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` + shared |

Compile/runtime env（DiT）：AdaStatic+Cg4 全套 + **`MLC_VLA_GR00T_DIT_SOFTADD=1`**。

接线：`BasicTransformerBlock.forward` → `flashrt.res_ln_fp8(hidden, attn_out, …)` → `ff.forward_from_prequant`；失败回落 add+`layer_norm_fp8`。

---

## Sanity（锁频，warmup=8 iters=40；vs same-session Cg4+SiluEpi lock）

| stage | Cg4+SiluEpi ref | **+DitSoftAdd** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.008 | 19.206 | +0.198 |
| backbone_llm | 17.441 | 17.664 | +0.223 |
| encode_condition | 5.283 | 5.094 | −0.189 |
| denoise_step | 14.276 | 13.506 | **−0.770** |
| **denoise_loop** | **44.249** | **42.610** | **−1.639** |
| e2e_head | 51.262 | 51.622 | +0.360 |
| **e2e_full** | **88.155** | **87.506** | **−0.649** |

### vs epic / Soft 估带

| | 估 | **merge sanity** |
|---|---:|---:|
| Δe2e_full | −0.2～−0.8 | **−0.649**（落估带中上） |
| Δdenoise_loop | ≲ add2~1.37 | **−1.639**（含 launch；高于纯 GPU 天花板，墙钟合理） |
| 明确赢门槛 | Δe2e ≤ −0.2 | **PASS** |

相对锁基线旧值 89.772：本 merge session 的 Cg4+SiluEpi ref 抖到 88.155；**合入后权威墙钟以本表 cand = 87.506 为准**（≈11.43 Hz）。距 66.7 仍 ~20.8 ms。

> bb 未改；vision/llm 抖动记会话噪声；刀收益以 **denoise_loop −1.639** / **e2e_full −0.649** 为准。

### Accuracy（denoise_loop actions，vs Cg4 lock DiT）

| | value | gate |
|---|---:|---|
| overall cos | **1.0** | >0.999 ✅ |
| overall mse | **0** | <0.0005 ✅ |
| overall mean_abs | **0** | — |
| per-dim pass | **132 / 132** | bit-identical |

完整：`ditsoftadd_gate_vs_cg4.json`。

### Pack 核确认

`strings model.so`：cand `flashrt_res_ln_fp8`×19 vs ref×6 → SoftAdd 已进图。

---

## Git commit

| repo | branch | SHA | message（首行） | push |
|---|---|---|---|---|
| `mlc-vla` | `feat/gelu-fp8-synapsex` | `03604486355c84939f1133a0af05c1833bff1f3a` | `feat(dit): DitSoftAdd res_ln_fp8 glue（attn residual⊕LN→e4m3）` | **已 push** → `r` |

### Files

**mlc-vla**
- `python/mlc_vla/model/gr00t_n17/modules_dit.py`（`MLC_VLA_GR00T_DIT_SOFTADD` → `flashrt.res_ln_fp8`）

未碰 synapsex（核已在 mlc-vla flashrt shim）；未动 QK/softmax/PV；未开 DitGemm。

---

## Artifacts

- Report: `/home/nio/shared/gr00t-fp8/gr00t-ditsoftadd-merge.md`
- Thor: `/work/gr00t_fp8_phase_a/ditsoftadd_merge_bench/measure_summary.json`
- Pack DiT: `/work/gr00t_fp8_phase_a/gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_cg4_softadd_unirt`
- Gate: `ditsoftadd_gate_vs_cg4.json`
- Epic: `gr00t-b1-denoise-hard-epic.md`

## 建议

DitSoftAdd **GO glue 已合**；e2e_full **~87.5 ms**。DitGemm 仍等 SoftAdd 后另排（本轮 NO）。
