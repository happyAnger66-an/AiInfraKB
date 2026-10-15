# GR00T DitRes scout — 环内残留 FP16 Linear + 残 quantize

- Date: 2026-10-15 ~09:45 Asia/Shanghai
- Status: **nsys 钉名 + 估 Δ only**；**未改代码 / 未编 pack / 未合基线**
- Baseline: **L1+L3+D1+crosskv**（DiT `..._phase_ada_ln_d1_crosskv_unirt` + bb `..._l3_o_down_i4_unirt`）
- 验收口径：e2e_full；禁降步；不重放 V1；**不抢 AdaStatic**（同文件退让）
- Thor: `thor-2239` / `pi05-forge-agent`；nsys 源 `dr_crosskv_bench/nsys`（12 iters，GPU ~48.5 ms/loop）
- 边界：接线若做 → **mlc-vla only**；新核 → synapsex；本 scout **零改动**

---

## Verdict: **SOFT-GO（可选填缝，默认不合）**

| | |
|---|---|
| 估 Δe2e_full（修订） | **−0.1～−0.5 ms**（inventory −0.5～−1.5 **偏乐观**） |
| 环内真残留 FP16 **Linear** | 几乎只剩 **`proj_out_2` ~0.064 ms/loop** |
| 残 quantize | **0.412 ms / 144L** = A2 `to_out` 税；清掉需 **attn→e4m3**，超出本刀「Linear→FP8」 |
| 廉价 smoke | **未跑**（需 calib+新 pack ~2.2G；`/work` 96%；且会改 `modules_dit.py`/`fp8.py` 与 AdaStatic 冲突） |
| 默认 | **不合**；让路 AdaStatic / D1take；AdaStatic 落地后再视填缝 |

**一句话：** 环内可 FP8 的 Linear 天花板太矮；quantize 大头不在 Linear 而在 attn 出口 Q。DitRes 作主刀 **不值**；作 Soft 填缝可记一笔。

---

## 1. 残留清单（D1+crosskv denoise_loop nsys）

### 1.1 FP16 GEMM / quantize（ms/loop，L/loop）

| kernel | ms/loop | L/loop | 归属 | DitRes? |
|---|---:|---:|---|---|
| `nvjet_192×8` bias | **2.054** | 33 | D1 AdaLN bank + `proj_out_1`（**环外**） | ❌ → **AdaStatic** |
| `quantize_fp8_fp16` | **0.412** | 144 | A2 attn `to_out` 前 Q（32/step 量级 + 余量） | ⚠️ 清税需 attn→e4m3，非本刀 |
| `cutlass_75_wmma` f16 32×32 | **0.398** | 64 | **attn PV**（probs@V；AttnScore 改 QK 后仍 64L） | ❌ → DitSoftAdd |
| `nvjet_64×48` NNT | **0.306** | 64 | **attn PV** 另一 shape（self/cross） | ❌ → DitSoftAdd |
| `nvjet_56×64` bias TNN | **0.064** | **4** | **`proj_out_2` [1024,1536]** 1/step | ✅ **本刀唯一主目标** |
| 其它 4L 小核合计 | ~0.14 | 4 each | 边角 / 非明确 Linear | 低优先 / 勿瞎归 |
| 1L 小核 | ~0.07 | 1 | 环一次 | 忽略 |

**AttnScore 对照（因果）：** cross QK→f16 后 magma 128→64、新出现 `nvjet_hss`×64；**wmma/nvjet_64×48 仍 64L** → 证实二者不是 QK、也不是 `proj_out_*`。

### 1.2 仍为 FP16 的 Linear（preset `e4m3_gr00t_dit` exclude）

| module | shape (out,in) | 运行时位置 | 处理现状 |
|---|---|---|---|
| `transformer_blocks.*.norm1.linear` | [3072, 1536] ×32 | 曾环内；现 **D1 环外 bank** | 勿 FP8（π0 同）；AdaStatic bake |
| `proj_out_1` | [3072, 1536] | D1 环外 | 同上 |
| `timestep_encoder` linear_1/2 | [1536,256]/[1536,1536] | D1 环外 | 同上 |
| **`proj_out_2`** | **[1024, 1536]** | **每步环内**（依赖 h） | **唯一不可环外预计算的残留 Linear** |

权重核对（ckpt）：`action_head.model.proj_out_2.weight` (1024, 1536)。

### 1.3 quantize 144L 拆解（机制，非再测）

crosskv 已把 quantize 192→144（−48 = cross K/V 共享 ×3 步）。剩余 ≈ **A2 `quantize_fp8` → `to_out.forward_prequantized`**（attn 出口仍 half）。  
`ada_ln_fp8` / `gelu_fp8` / `layer_norm_fp8` 已消掉 QKV/FFN 入口 Q。  
→ **再砍 0.41 ms 的正道是 attn pack/epi 直出 e4m3**，不是给 `proj_out_2` 套 FP8。

---

## 2. 估 Δ（修订 inventory）

| 杠杆 | 乐观 GPU | 现实 e2e | 备注 |
|---|---:|---:|---|
| `proj_out_2` → FP8（± `norm_out→e4m3` prequant） | ≤0.06 | **−0.05～−0.2** | 小 M；Q 税可能吃光；需新 calib |
| 清全部 residual quantize 0.41 | 0.41 | **−0.3～−0.5** | **依赖新 epi / 非 Linear 刀** |
| 误把 PV 0.70 算进 DitRes | — | — | **禁止**；属 DitSoftAdd |
| **本刀合规合计** | | **−0.1～−0.5** | vs inventory −0.5～−1.5 |

相对 gap ~37 ms：**可忽略**。不挡 15Hz 叙事。

---

## 3. 若日后落地（设计草稿，本轮不做）

1. **preset**：`e4m3_gr00t_dit` include 增 `model.proj_out_2`；exclude 仍留 AdaLN/timestep/`proj_out_1`。  
2. **calib**：为 `proj_out_2` 补 `input_scale`（现有 `fp8_scales.npz` **无** proj_out 键）。  
3. **接线**（mlc-vla）：`norm_out` affine-free → 复用 `layer_norm_fp8(ones/zeros)` → `proj_out_2.forward_prequantized`；开关如 `MLC_VLA_GR00T_PROJ_OUT_FP8`。  
4. **勿动** synapsex（无新核）；勿碰 AdaStatic / D1take 同改区。  
5. 验收：lockfreq stages + overall gate vs L1+L3+D1+crosskv；nsys 看 `nvjet_56×64` 是否消失、quantize L 是否仍 144（预期 **仍在**——本刀不消 to_out Q）。

**Smoke 未跑理由：** 非廉价（重编 + calib + 2.2G pack）；磁盘 96%；与 AdaStatic 抢 `modules_dit.py`；ROI 先验不足。

---

## 4. Go / no-go 表

| verdict | **SOFT-GO** |
|---|---|
| Why soft | 路径清晰、风险低、与 AdaStatic 正交（目标层不同）；但 **e2e 先验 <0.5 ms** |
| Why 默认不合 | 填不满 gap；编包成本高；quantize 主税不在范围 |
| 何时升级 GO 测 | AdaStatic+D1take 合完仍要抠小数，且磁盘/文件无冲突 |
| Do **not** | 把 PV/wmma 算进本刀；重放 V1；动 AdaLN→FP8；降步 |

---

## 5. Artifacts / 指针

| | |
|---|---|
| 本报告 | `/home/nio/shared/gr00t-fp8/gr00t-ditres-scout.md` |
| nsys | Thor `dr_crosskv_bench/nsys/dr_crosskv_denoise_loop_kern_cuda_gpu_kern_sum.csv` |
| parse | LT5 `nsys_baseline_parse.json` / `gap_meta.json` |
| inventory | `gr00t-15hz-gap-inventory-v2.md` §DitRes |
| 前序 | `gr00t-d1-residual-gemm-report.md` / `gr00t-denoise-residual-fuse-report.md` |
| AttnScore 对照 | `gr00t-attn-score-cross-f16.md`（证 PV≠QK） |

---

## 6. Ask（给架构师）

1. 接受修订估 **−0.1～−0.5** 与 **SOFT-GO 默认不合**？  
2. quantize 0.41 若要啃，是否另开 **DitAttnE4**（attn→e4m3）ID，而不是塞进 DitRes？  
3. 本轮主刀继续 **AdaStatic**；DitRes 仅 backlog。
