# GR00T Cg4 merge — cudagraph@4 叠入 L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic

- Date: 2026-10-15 11:20 Asia/Shanghai
- Status: **MERGED**；基线指针已更新；**已 push**
- Prior: dparallel scout（`--cuda-graph` @4；loop −7.6；hybrid e2e 噪声）；架构师批 **Cg4 并行合**
- This merge: **Cg4** = denoise compile `--cuda-graph`，**保持 `num_inference_timesteps=4`**（**禁 2-step**）

---

## 合入状态：**DONE**

| 项 | 值 |
|---|---|
| Stack | **L1 + L3 + LlmRmsQ + EncFp8 + D1 + crosskv + D1take + AdaStatic + Cg4** |
| DiT raw | `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_cg4_unirt` |
| DiT 新别名（canonical） | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` → 上 |
| DiT Cg4 别名 | `..._AdaStatic_Cg4_unirt` → 上 |
| DiT pre-Cg4 | `..._AdaStatic_pre_Cg4_unirt` → `..._take_fuse_adastatic_unirt` |
| bb | `gr00t_n17_bb_fp8_l3_qkv_rmsq_enc_i4_unirt`（未改） |
| CURRENT_BASELINE | `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` + shared 已升本栈 |

Compile：AdaStatic 全套 env + `--set static_ada_ln_bank=true` + **`--cuda-graph`**；compile describe 确认 `"cuda_graph": true`；pack attrs `num_inference_timesteps=4`。

源码：`_materialize_for_cudagraph`（π0 同构）物化 `vl_embs` / `state_features`（float 恒等）。**本轮实测 pack 为 flag-only `--cuda-graph`**（materialize 已进 git，下次重编自动 bake；本 pack bit-identical 已过 gate）。

---

## Sanity（锁频，warmup=8 iters=40；vs same-session AdaStatic）

| stage | AdaStatic ref | **+Cg4** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.418 | 19.307 | −0.111 |
| backbone_llm | 18.327 | 18.417 | +0.090 |
| encode_condition | 5.214 | 5.203 | −0.011 |
| denoise_step | 16.325 | 13.812 | **−2.513** |
| **denoise_loop** | **49.173** | **43.540** | **−5.633** |
| **e2e_head** | **58.773** | **52.998** | **−5.775** |
| **e2e_full** | **96.435** | **90.295** | **−6.140** |

权威墙钟以本表 cand = **90.295** 为准（≈11.07 Hz）。相对锁基线旧值 95.513：本 session AdaStatic ref 抖到 96.435；**刀收益以 same-session Δe2e −6.140 / Δloop −5.633 为准**。距 66.7 仍 ~23.6 ms。

> bb 舞台抖动 ≤0.1 ms；刀收益在 denoise（Cg4 只动 DiT）。

### Accuracy（denoise_loop actions，vs AdaStatic DiT）

| | value | gate |
|---|---:|---|
| overall cos | **1.0** | >0.999 ✅ |
| overall mse | **0.0** | <0.0005 ✅ |
| overall mean_abs | **0.0** | — |
| per-dim pass | **132 / 132** | ✅ |

bit-identical（capture/replay 不改数值）。

---

## Git commit

| | |
|---|---|
| Repo | `mlc-vla`（`feat/gelu-fp8-synapsex` / r-infra） |
| Scope | **仅 Cg4**：`_materialize_for_cudagraph` + denoise_loop float 入参物化 |
| **不含** | DitSoftAdd / SoftAdd WIP（已 stash，未混入） |
| Push | `r/feat/gelu-fp8-synapsex` @ `ce568f3` |
| SHA | `ce568f301076dc20879dad9acdd56a50f4c3237e` |

---

## Artifacts

- Report: `/home/nio/shared/gr00t-fp8/gr00t-cg4-merge.md`
- Thor: `/work/gr00t_fp8_phase_a/cg4_merge_bench/measure_summary.json`
- Pack: `/work/gr00t_fp8_phase_a/gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_adastatic_cg4_unirt`
- Alias: `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` / `..._Cg4_unirt`
- Gate: `cg4_gate_vs_adastatic.json`（shared 副本）

## 建议

Cg4 **GO 已合**；e2e_full **~90.3 ms**。不自批下一刀（DitSoftAdd 出数再批；LlmSiluEpi 仅设计 scout）。
