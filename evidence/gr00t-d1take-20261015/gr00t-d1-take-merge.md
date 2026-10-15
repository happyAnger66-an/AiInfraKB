# GR00T D1take merge — baseline bump

- Date: 2026-10-15 ~09:40 Asia/Shanghai
- Architect: **批合 D1take**（SOFT-GO → 合）
- New baseline stack: **L1 + L3 + D1 + crosskv + D1take**
- e2e_full band: **~102 ms**
- AdaStatic: **untouched**
- Git: **no commit/push**（与既往 L1/L3/D1/crosskv 合入一致；源码 default-on + pack 升格）

---

## 合入点

| layer | what |
|---|---|
| Source (Thor `/srcs/data/mlc-vla` = apex_rt) | `MLC_VLA_GR00T_ADA_LN_BANK_STEP` **default True**；`flashrt_ada_ln_fp8_step` + shim `_ada_ln_mod_row_ptr`；`model.denoise_loop` / `modules_dit` `ada_step` |
| Source (LT5 `r-infra/mlc-vla`) | 已从 Thor 同步同四文件（`model.py` / `modules_dit.py` / `shim.cu` / `__init__.py`） |
| DiT pack (raw) | `gr00t_n17_dit_fp8_full_dit_phase_ada_ln_d1_crosskv_take_fuse_unirt` |
| DiT pack (canonical alias) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_unirt` → take_fuse |
| BB pack | `gr00t_n17_bb_fp8_l3_o_down_i4_unirt`（不变） |
| Pointer doc | `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` |
| Prior DiT kept | `..._d1_crosskv_unirt`（A/B 对照，不删） |

## Sanity（锁频 GATE PASS；warmup=8 iters=40）

| stage | median ms |
|---|---:|
| embed_vision | 19.430 |
| backbone_llm | 19.970 |
| encode_condition | 6.713 |
| denoise_step | 15.975 |
| denoise_loop | 51.945 |
| e2e_head | 63.370 |
| **e2e_full** | **102.734** |

- vs pre-D1take accuracy: cos=1.0, mse=0.0, mabs=0.0 → **bit-identical PASS**
- Measure report e2e was 102.033；sanity e2e **102.734**（同 ~102 带）

## Notes

- 首轮 sanity 曾见 e2e~110（疑会话污染）；以 **r2 锁频空闲** `stages_sanity_r2.json` 为准。
- 未开新刀；未动 AdaStatic。

## Artifacts

- Thor alias: `/work/gr00t_fp8_phase_a/gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_unirt`
- Thor CURRENT_BASELINE: `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md`
- Shared: `gr00t-d1-take-merge.md`, `CURRENT_BASELINE.md`, `stages_sanity_r2.json`, `gate_vs_pre_d1take.json`
- Evidence: `gr00t-d1-take-fuse-report.md`
