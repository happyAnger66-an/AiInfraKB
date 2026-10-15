# GR00T LlmRmsQ merge — 叠入 L1+L3+D1+crosskv+D1take+AdaStatic

- Date: 2026-10-15 Asia/Shanghai (~10:36)
- Status: **MERGED**；基线指针已更新；**无 git push / 无 commit**
- Prior scout: `gr00t-llmrmsq-scout.md`（Soft-GO → 架构师升 **GO**；e2e −2.02 / llm −1.64）
- This merge: **LlmRmsQ** = L3 bb + QKV FP8 + `rms_fp8`→shared QKV prequant

---

## 合入状态：**DONE**

| 项 | 值 |
|---|---|
| Stack | **L1 + L3 + LlmRmsQ + D1 + crosskv + D1take + AdaStatic** |
| bb (canonical) | `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_qkv_rmsq_i4_unirt` |
| bb (prior L3) | `gr00t_n17_bb_fp8_baseline_L1L3_pre_LlmRmsQ_unirt` → `gr00t_n17_bb_fp8_l3_o_down_i4_unirt` |
| DiT (unchanged) | `gr00t_n17_dit_fp8_baseline_L1L3D1crosskv_D1take_AdaStatic_unirt` → `..._take_fuse_adastatic_unirt` |
| CURRENT_BASELINE | `/work/gr00t_fp8_phase_a/CURRENT_BASELINE.md` + shared 已升本栈 |

Compile/runtime env（bb）：`LLM_RMS_FP8=1` + `LLM_QKV_SHARED_FP8=1` + L3 O/DOWN；preset `e4m3_gr00t_llm_l3_qkv`（112 Linear）。

`w−1` Soft-GO：**不挡合入**；报告记可跟（Qwen `rms_fp8_mulw` / fold-LN），**本轮不挖**。

---

## Sanity（锁频，warmup=8 iters=40；vs pre-merge L3+AdaStatic）

| stage | L3+AdaStatic | **+LlmRmsQ** | Δ |
|---|---:|---:|---:|
| embed_vision | 19.172 | 19.291 | +0.119 |
| **backbone_llm** | **20.258** | **18.924** | **−1.334** |
| encode_condition | 6.491 | 6.829 | +0.337 |
| denoise_step | 15.933 | 16.045 | +0.111 |
| denoise_loop | 49.465 | 49.691 | +0.226 |
| **e2e_head** | **60.648** | **60.680** | **+0.032** |
| **e2e_full** | **100.181** | **98.432** | **−1.750** |

### vs scout 对照

| | scout (vs L3 same-session) | **merge sanity** |
|---|---:|---:|
| Δe2e_full | −2.024 | **−1.750** |
| Δbackbone_llm | −1.638 | **−1.334** |
| 量级 | 同档（会话抖） | 同档 |

相对锁基线旧值 99.347：本 merge session 的 L3 ref 抖到 100.18；**合入后权威墙钟以本表 cand = 98.432 为准**（≈10.2 Hz）。距 66.7 仍 ~31.7 ms。

### Accuracy（denoise_loop actions，vs pre-merge L3 bb）

| | value | gate |
|---|---:|---|
| overall cos | **0.999939** | >0.999 ✅ |
| overall mse | **1.465e-04** | <0.0005 ✅（scout FP16 门 4.58e-4 贴门；相对 L3 更宽裕） |
| overall mean_abs | **5.436e-03** | — |
| per-dim pass | **116 / 132**（0–31 见 json） | report |
| backbone_llm cos (L3 vs cand) | 0.7845 | soft |

完整 per-dim：`llmrmsq_merge_bench/gate_vs_l3.json`。

---

## 建议

e2e_full **~98.4 ms** 已锁为新速度基线（`CURRENT_BASELINE.md` 已指向）。**不要**开 EncFp8 / 重放 L2/V1/AttnScore/DitAttnE4。下一刀等架构师。

---

## Artifacts

- Report: `/home/nio/shared/gr00t-fp8/gr00t-llmrmsq-merge.md`
- Thor: `/work/gr00t_fp8_phase_a/llmrmsq_merge_bench/measure_summary.json`
- Pack bb: `/work/gr00t_fp8_phase_a/gr00t_n17_bb_fp8_l3_qkv_rmsq_i4_unirt`
- Alias: `gr00t_n17_bb_fp8_baseline_L1L3LlmRmsQ_unirt`
- Scout: `gr00t-llmrmsq-scout.md`
