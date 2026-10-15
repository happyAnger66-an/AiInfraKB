# GR00T B2 — Vision Soft 清税 scout（`res_ln_fp8` / `o_half_in`）

- Date: 2026-10-15 Asia/Shanghai (~12:00)
- Status: **scout only**（可迁证明 + 估 Δ + Soft-GO）；**未 wire / 未编包 / 不合入**
- Hill gate: overall **cos>0.999 AND mse<0.0005**；验收 **e2e_full**
- Steering: quant / fusion / ops / precompute only — **禁** VisNonV1 plain / V1 plain；**禁** 2-step
- Machine: LT5（读码 + 既有 nsys/墙钟）；执行 Thor 时 `FLASHRT_ROOT=/srcs/data/FlashRT`（核本体已在 mlc-vla `kernels/flashrt`）
- Lock baseline: **L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi** → e2e_full **89.772** / embed_vision **19.338**（`CURRENT_BASELINE.md`）

---

## Verdict

| | |
|---|---|
| **Go / Soft / no-go** | **Soft-GO**（默认可开 glue+measure；**默认不合入**） |
| **可迁** | **YES** |
| 估 Δembed_vision | **−0 ～ −2.5 ms**（中枢约 −0.5～−1.5；叠 V1b 可达 −0.5～−3） |
| 估 Δe2e_full | **−0 ～ −2.5 ms**（bb-only；与 embed 同量级） |
| overall gate（预期） | 可过（VisNonV1 / V1b 先例 overall PASS；feature cos 仍软，需链式门控） |
| 相对 66.7 | Soft 满成仍 ~87–90；**冲不满** 15 Hz |

**One-liner:** π0 `res_ln_fp8` + `vit_fp8_o_half_in` **可迁到 GR00T ViT**（拓扑同构、dim=1024 走通用 f16 路径、核已在 mlc-vla FlashRT）；目标是杀掉 VisNonV1 已证的 **`quantize_fp8` 税**并吸收 residual+LN，而不是再跑 plain Linear。估 e2e **−0～−2.5**；需 glue 后 lockfreq+nsys 实证，**默认不合**。

---

## 1. 可迁结论（YES + 边界）

### 1.1 核 / BYOC 是否存在

| 杠杆 | 形态 | 落点（LT5 树） | GR00T 现状 |
|---|---|---|---|
| **`res_ln_fp8`** | FlashRT CUDA：`r=residual+x` + `e4m3(LN(r)/scale)` 一发 | `mlc-vla/.../kernels/flashrt/layer_norm_fp8.cuh` + `shim.cu` + `__init__.py::res_ln_fp8` | **未接线**（无 `vit_fp8_res_ln` / `forward_fused`） |
| **`layer_norm_fp8`** | 首层无 residual 时的 LN→e4m3 | 同上 | 未接线 |
| **`vit_fp8_o_half_in`** | **非新核**：half→`/scale`→e4m3 与 `out_proj` 同 BYOC partition → cutlass **BiasFromHalf** | π0 `siglip.py::_out_proj`；synapsex `TryCutlassSm100Fp8GemmBiasFromHalf` | GR00T `VisionAttention` 仍 `self.proj(out)`；VisNonV1 plain 用独立 `quantize_fp8`（已 NO-GO） |
| V1b（相关、可选叠） | BiasGelu→e4m3 epi | GR00T 已有 `vit_fp8_fc1_gelu_q_epi` | Soft 可选；历史 embed **−0.8～−0.9**；feature 软；未合基线 |

`FLASHRT_ROOT=/srcs/data/FlashRT` 为 Thor 运行约定；**scout 所依赖的 `res_ln_fp8` 实现已 vendored 进 mlc-vla**，不依赖另开 FlashRT 新核 epic。

### 1.2 形状 / dim

| | π0 SigLIP | **GR00T Qwen3 ViT** | 结论 |
|---|---|---|---|
| hidden | **1152**（专用 `*_d1152` kernel） | **1024** | 走 **通用** `res_ln_fp8_kernel_f16`；`kLnFp8MaxDim=4096`，1024 偶数 ✅ |
| tokens | 依 cam/patch | 6×256=**1536** rows | 核按 row 启动，无阻 |
| LN | `LayerNorm` + γ/β | `nn.LayerNorm(dim, elementwise_affine=True)` | ✅ `layer_norm_fp8_supported` |
| 下一 GEMM | FP8Linear qkv / fc1 | 需 preset 全层 FP8（见下） | 条件可满足，**当前锁 bb 未开** |

### 1.3 拓扑同构

π0 `SiglipEncoderLayer.forward_fused`：

```
res, x_q = res_ln_fp8(res, delta, ln1, qkv_scale)   # or layer_norm_fp8 首层
attn_out = attn.forward_from_prequant(x_q)
res, mlp_q = res_ln_fp8(res, attn_out, ln2, fc1_scale)
delta_mlp = mlp.forward_from_prequant(mlp_q)
```

GR00T `VisionBlock.forward` 今日：

```
x = x + attn(norm1(x), rope, ...)
x = x + mlp(norm2(x))
```

→ **同一 pre-LN residual 结构**。RoPE / flash / chunk_sizes 在 attn **内部**、`res_ln` **之后**，不挡 LN→e4m3→qkv.prequant。  
PatchMerger / deepstack **不进本 Soft MVP**（与 π0 主刀 encoder layer 对齐）。

### 1.4 与当前锁 pack 的缺口（为何不是 flag-on）

锁 bb = L1+L3+LlmRmsQ+Enc+SiluMul；**ViT 仍 FP16**。GR00T `config.py` 仅有 `vit_fp8_fc1_gelu_q_epi`；**无** `vit_fp8_res_ln` / `vit_fp8_o_half_in`。  
LT5 `modules_vit.py` 的 `VisionAttention` **无** VisNonV1 env 钩子（该刀在 Thor apex_rt 测过，默认不合）。

可迁 = **可搬 glue**，不是「现成 alias 一开」。需要：

1. `VisionBlock.forward_fused`（抄 π0，带 RoPE 参数透传）
2. `VisionAttention.forward_from_prequant` + `_out_proj` half_in 分支
3. `VisionMLP.forward_from_prequant`（可复用 V1b 图）
4. config：`vit_fp8_res_ln` / `vit_fp8_o_half_in`；preset：**attn+MLP 全层 FP8Linear**（禁只开 plain shared-Q）
5. BYOC：确认 Thor `tvm-relax` **half_in / BiasFromHalf** 注册序（V1b 0047 先例：错序会出独立 Q）
6. calib：real-act scales（VisNonV1/V1 合成 calib → feature cos 软）

### 1.5 明确不可迁 / 禁止路径

| 路径 | 结论 | 证据 |
|---|---|---|
| **VisNonV1 plain**（attn FP8 + 独立 `quantize_fp8`） | **禁重测** | embed **+1.37** / e2e **+1.48**；`gr00t-visnonv1-attn-fp8-scout.md` |
| **V1 plain**（拆 gelu_fp8） | **禁** | embed **+1.5～+2.2** |
| 无 FP8Linear 却开 `res_ln_fp8` | 建图必炸 | π0：`vit_fp8_res_ln 需要 qkv/fc1 为 FP8Linear` |
| 只开 O-Q 瘦 `quantize_fp8` 当 Soft | **不算 Soft** | 正是 VisNonV1 税源；必须 **half_in BYOC** |

**可迁总结：YES** — 核与拓扑就绪；工程是 synapsex/BYOC 已有能力上的 **mlc-vla glue + calib + 新 bb pack**，非挖新 CUDA epic。

---

## 2. 估 Δ（相对锁基线 ~89.8 / Vision ~19.3）

### 2.1 证据链（非本刀新测；外推）

**VisNonV1 nsys（embed；12 iters；相对同会话 L3 FP16-ViT attn）** — `visnonv1_nsys_ab_summary.json`：

| 项 | L3 FP16-vis | VisNonV1 | 解读 |
|---|---:|---:|---|
| `quantize_fp8` | 0 | **~0.57 ms/iter** | Soft 主杀目标（O + 入口 Q） |
| nvjet + cutlass GEMM 合计 | ~10.10 | ~9.33 | **GEMM 净 −0.77**（FP8 并不慢） |
| `layer_norm_kernel` | ~1.33 | ~1.33 | Soft `res_ln` 替换之，并吃掉残差 add |
| 墙钟 embed Δ | — | **+1.37** | ≈ Q 税 0.57 + 非 Q 开销 ~0.8（add/layout 等） |

→ plain 回归主因是 **税与拆融合**，不是「FP8 GEMM 必输」。清税后符号**有机会翻正**，但非保证。

**V1b（历史，L1 会话）**：BiasGeluE4m3 HIT；embed **−0.81～−0.92**；e2e **−0.5～−1.2**；feature cos~0.74 软 — Soft 菜单可**可选叠**，不当本 scout 必做。

### 2.2 估带（Soft = `res_ln_fp8` + `o_half_in`，全层 FP8，禁 plain Q）

| 场景 | Δembed_vision | Δe2e_full | 条件 |
|---|---:|---:|---|
| **悲观** | **0 ～ +0.5** | **0 ～ +0.5** | half_in 未 HIT / 仍漏 Q；或 layout 税未消 |
| **中枢（Soft-GO 预期）** | **−0.5 ～ −1.5** | **−0.5 ～ −1.5** | Q 税尽杀；res_ln 吸收部分 add+LN；GEMM 保持 VisNonV1 级净利 |
| **乐观 Soft** | **−1.5 ～ −2.5** | **−1.5 ～ −2.5** | 清税 + residual/LN 合并顺；无大噪声 |
| Soft **+ V1b** 乐观 | **−0.5 ～ −3.0** | **−0.5 ～ −3.0** | V1b 历史 −0.8 可叠加；交互未测 |

与 gap inventory v4「Vision Soft **−0～−3?**」一致；本 scout **收窄中枢到 −0.5～−1.5**，并钉死 **可迁 YES**。

**不承诺**逼近 66.7：满成 Soft(+V1b) 后 e2e 仍约 **87–90**。

---

## 3. nsys / 对照要点（glue 后怎么验）

### 3.1 对照设计

| | |
|---|---|
| Ref | 锁基线 bb（SiluMul）+ 锁 DiT（Cg4）；**同会话** |
| Cand | 新 pack：`vit_fp8_res_ln=true` + `vit_fp8_o_half_in=true` + 全层 ViT FP8 preset（± 可选 `vit_fp8_fc1_gelu_q_epi`） |
| **禁** | `VIT_ATTN_SHARED_FP8` plain / 独立 `quantize_fp8` 当主路径 |
| 墙钟 | lockfreq；warmup≥8 / iters≥40；报 embed + e2e_full |
| 精度 | overall vs 锁 bb → 共享 DiT；**另报** embed feature cos； ideally 链式 embed→llm→… |

### 3.2 nsys HIT / MISS（embed_vision）

| 信号 | Soft HIT | MISS（停合 / 当 VisNonV1 回退） |
|---|---|---|
| `quantize_fp8_fp16_kernel` | **~0** | 仍有按层 launch → half_in / res_ln 未吃到 |
| `res_ln_fp8` / `layer_norm_fp8` 核名 | 有（替换大量 `layer_norm_kernel`） | 仍满额 `layer_norm_kernel` + 独立 add |
| BiasFromHalf / half_in epi on `out_proj` | cutlass 名含 FromHalf 或等价 | 仍 half GEMM + 外置 Q |
| FP8 GEMM vs 基线 nvjet | 允许；看**净值** | 若 +Q 再回 VisNonV1 形态 → NO-GO |
| 墙钟 embed | ≤0 且最好 ≤ −0.5 | embed **> +0.3** 稳态 → Soft 失败 |

### 3.3 精度门

- overall：cos>0.999 且 mse<0.0005（硬）
- embed feature：VisNonV1~0.99 / V1b~0.74 软；Soft 应用 **real-act calib**，目标尽量 ≥0.99；不达不单凭 overall 喊 GO 合入

---

## 4. 建议下一拍（不自批合入）

1. **Soft-GO → glue epic（小）**：`modules_vit` + config + preset + calib；新 pack 名，**不覆盖**锁 bb alias。  
2. Thor lockfreq A/B + nsys（上表 HIT 清单）。  
3. 架构师按数批：embed≤−0.5 且 gate PASS → 可议合；否则 **NO-GO / 停**。  
4. **并行**：B1 Denoise 硬啃不受本结论阻塞。  
5. 勿把 Soft 写成「再跑一遍 VisNonV1」。

---

## 5. Artifacts / 指针

| 文件 | 用途 |
|---|---|
| **本报告** | `/home/nio/shared/gr00t-fp8/gr00t-vision-soft-scout.md` |
| 锁基线 | `CURRENT_BASELINE.md`（e2e **89.772** / vision **19.338**） |
| VisNonV1 NO-GO | `gr00t-visnonv1-attn-fp8-scout.md` + `visnonv1_nsys_ab_summary.json` |
| V1 / V1b | `gr00t-v1-vision-mlp-report.md` / `gr00t-v1b-fused-epi-report.md` |
| gap | `gr00t-15hz-gap-inventory-v4.md` § Vision Soft |
| π0 参考 | `mlc-vla/.../model/pi0/siglip.py`（`forward_fused` / `_out_proj`） |
| 核 | `mlc-vla/.../kernels/flashrt/layer_norm_fp8.cuh` |

---

## 6. Ask 架构师

1. Soft-GO 是否批 **glue+measure**（默认可）？合入门槛是否采用「embed ≤ −0.5 且 overall PASS」？  
2. Soft MVP 是否 **强制叠 V1b**，还是先 res_ln+o_half_in only？  
3. B1 / B2 并行时 bb pack 命名隔离是否按「新名字 only、不碰锁 alias」执行？
