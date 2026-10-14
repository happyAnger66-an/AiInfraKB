# GR00T L3 o/down FP8 vs L2 QKV — 证据摘要

来源：gr00t优化项目群 2026-10-14/15；报告 `gr00t-l3-o-down-scout.md`、`gr00t-l2-qkv-fp8-report.md`；架构师批 L3 合、L2 不合。

## L3（合）

- preset：`e4m3_gr00t_llm_l3_o_down`（L1 gate+up + o_proj + down；**无 QKV**）
- llm **23.99→20.18（−3.8）**；e2e_full **107.7→103.5（−4.2）**
- overall PASS cos0.99997 mse7.8e-5；feature cos ~0.835
- nsys：nvjet 960→576（o+down FP16 路径清掉）

## L2（不合，对照）

- pack：`bb_fp8_l2_llm_mlp_qkv_i4`（QKV FP8）
- llm −0.27；e2e −0.75
- overall PASS，但 feature cos **0.88→0.78** 变差
- nsys：QKV→FP8 成立，净仅 ~0.6 ms/iter；o/down 仍 nvjet

## 结论对比

| | L3 o/down | L2 QKV |
|---|---|---|
| e2e 收益 | −4.2 ms | −0.75 ms |
| feature cos | ~0.835（可接受） | 0.88→0.78（变差） |
| nsys 因果 | 清掉 o/down nvjet | Q 税薄利，残留 o/down |
| 决策 | **合** | **不合** |

合入基线：`L1+L3+D1+crosskv`（e2e_full ~103.5）。
