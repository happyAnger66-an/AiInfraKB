# GR00T AdaStatic scout — 固定 4-step bake AdaLN/proj（π0 0034）

- Date: 2026-10-15 Asia/Shanghai (~09:42)
- Status: **measured**; **default NO merge**（等架构师批）
- Baseline: bb `gr00t_n17_bb_fp8_l3_o_down_i4_unirt` + DiT `..._phase_ada_ln_d1_crosskv_unirt` (**L1+L3+D1+crosskv**)
- Candidate DiT: `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_adastatic_unirt`
- Isolate: `MLC_VLA_GR00T_ADA_LN_BANK_STEP=0`（本刀不叠 D1take）；Vision 不开；禁降步
- Thor: lockfreq GATE PASS；warmup=8 iters=40
- Est: e2e **−1.5～−3.5**（砍环外 nvjet_192×8 ~2 ms）

---

## Verdict: **GO**

| call | meaning |
|---|---|
| **GO** | e2e_full **−2.62** 落在估内；精度 overall+per-dim **PASS**；pack 折表非零 |
| **默认不合** | 等架构师批升基线；可与 D1take（刚测 ~−1.2）正交叠 |

**Default merge posture:** 不合；合前确认与 D1take 叠测（可选）。

---

## 1. Stages（p50 ms）

| stage | L3+D1+crosskv | +AdaStatic | Δ |
|---|---:|---:|---:|
| embed_vision | 19.078 | 19.105 | +0.027 |
| backbone_llm | 19.883 | 19.986 | +0.102 |
| encode_condition | 6.521 | 6.694 | +0.172 |
| denoise_step | 16.871 | 16.270 | **−0.601** |
| **denoise_loop** | **53.670** | **50.316** | **−3.354** |
| **e2e_head** | **63.322** | **61.332** | **−1.990** |
| **e2e_full** | **103.508** | **100.892** | **−2.615** |

验收口径 **e2e_full**：基线 ~103.5 → 候选 **~100.9**（约 **9.9 Hz**；距 15 Hz / 66.7 仍远）。

---

## 2. Accuracy（baseline DiT vs AdaStatic DiT，denoise_loop）

| | value | gate |
|---|---:|---|
| overall cos | **0.99999935** | >0.999 ✅ |
| overall mse | **1.59e-6** | <0.0005 ✅ |
| overall mean_abs | 9.1e-4 | — |
| per-dim pass | **132 / 132**（0–31: 32/32） | cos>0.999 & mse<5e-4 |

最弱 cos dim8=0.999566；最大 mse dim19=9.2e-6 — 均过门。完整 per-dim 见 `adastatic_bench/gate_vs_baseline.json`。

---

## 3. 做法（π0 0034 同构）

环外 D1 仍每帧算 `timestep_encoder([N]) + 32×AdaLN.linear + proj_out_1`（nsys 归 **nvjet_192×8 ~2 ms**）。AdaStatic：

1. **pack/load 折表**：固定 Euler `t_disc = int((t/N)*buckets)` → numpy 复刻 TimestepEncoder + 各层 `norm1.linear` + `proj_out_1` → 写入参数  
   - `adaln_static_scale_{i}` / `adaln_static_shift_{i}`：`[N,1,D]` ×32  
   - `proj_out_1_static`：`[N,2D]`
2. **图内**：`denoise_loop` 若存在 `adaln_static_scale_0`，直接读表（**无**环外 temb GEMM）；步内仍 take /（可选）bank+step。
3. **开关**：`--set static_ada_ln_bank=true` 或 `MLC_VLA_GR00T_ADA_LN_STATIC=1`；默认关。

只依赖固定 4-step 时间表 + 权重，**不**依赖 image/prompt/state；**不是**改采样步数。

---

## 4. 修改范围（mlc-vla DiT glue；synapsex 未动）

| 文件 | 改动 |
|---|---|
| `model/gr00t_n17/gr00t_host.py` | **新** `compute_static_ada_ln_bank` |
| `model/gr00t_n17/config.py` | `static_ada_ln_bank: bool = False` |
| `model/gr00t_n17/loader.py` | `fold_static_ada_ln_bank`（load 末尾） |
| `model/gr00t_n17/model.py` | 注册 static params；`denoise_loop` 读表路径 |

Pack 校验：候选 **1370** params vs 基线 **1305**（+65 static）；`adaln_static_scale_0` shape `[4,1,1536]` 非零。

路径：Thor host `~/xiaoning.zhao/apex_rt/mlc-vla`（= container `/srcs/data/mlc-vla`）。

---

## 5. nsys

本轮 **跳过**：e2e_full Δ **−2.62 ≤ −1.5** 且精度 PASS（交付：不达估或 FAIL 才强制 A/B）。  
归因预期：环外 **nvjet_192×8** 与相关 temb Linear 从 denoise_loop 序言消失；loop 墙钟 −3.35 与估同量级。

---

## 6. Ask / next

1. **AdaStatic：GO，默认不合** — 请架构师批是否升入基线（L1+L3+D1+crosskv+**AdaStatic** → e2e_full ~100.9）。
2. 与 **D1take**（同日测 e2e_full ~−1.2、bit-identical）正交，可另开叠测。
3. 即令叠上，距 e2e_full 66.7 仍约 **30+ ms**；下一刀按 inventory：**DitRes** 或另批更大路径。

---

## Artifacts

- Report: `/home/nio/shared/gr00t-fp8/gr00t-adastatic-scout.md`
- Thor bench: `/work/gr00t_fp8_phase_a/adastatic_bench/`（`measure_summary.json`, `stages_*.json`, `gate_vs_baseline.json`）
- Pack: `/work/gr00t_fp8_phase_a/gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_adastatic_unirt`
- Scripts: `run_adastatic.sh` / `run_adastatic_resume.sh`
