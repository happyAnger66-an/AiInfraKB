# GR00T VisNonV1 — ViT attn FP8 scout 证据摘要

来源：牛马 `gr00t-visnonv1-attn-fp8-scout.md`（2026-10-15）；架构师批 **NO-GO，不合**。

## Verdict

| 项 | 值 |
|---|---|
| 决策 | **NO-GO / 默认不合** |
| embed_vision | 19.52 → **20.89（+1.37）** |
| e2e_full | 99.64 → **101.12（+1.48）** |
| overall | cos 0.999966 / mse 8.13e-5 **PASS** |
| embed feature cos | ~0.9906 soft |
| nsys | shared-Q HIT；`quantize_fp8` ~0.57 ms/iter 吃掉 FP8 GEMM |

目标估 −2～−5 **未达成（符号相反）**。

## 一句话

ViT attn QKV/proj → FP8 + shared Q（禁 MLP）接线正确，但独立 Q 税 + 丢 nvjet fusion → embed/e2e 双回归；与 V1 plain 同病不同灶。续挖走 `res_ln_fp8` / `o_half_in` 清税，勿再 plain Linear。

## 架构师

NO-GO 确认；下一刀 **LlmRmsQ**（禁重放 L2/V1）；Vision Soft-GO backlog 本轮不抢。

全文见同目录 `gr00t-visnonv1-attn-fp8-scout.md`。
