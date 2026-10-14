# GR00T 消 `quantize1` 税 — 设计计划（不实施）

- 日期：2026-10-14
- 状态：Phase A **接线已落地（mlc-vla，未 commit/push）**；原设计节保留作背景
- 动机：全量 DiT FP8（192 Linear）锁频 **1.16–1.18×**；nsys `quantize*` **15.2%（2.39 ms）**；税=0 时理论 **~1.42×**
- 边界：后续 **kernel 实现进 synapsex**；mlc-vla 只接线；**禁止**把 DiT 专用 glue 塞进 synapsex

---

## 1. 今天 `quantize1_kernel` 从哪来？

### 发射链（编译期图 → 运行时核）

1. **模型侧（GR00T）**  
   - `mlc_vla/model/gr00t_n17/build.py`：`fp8_quant.quantize_model(...)` 把命中的 `nn.Linear` 换成 `FP8Linear`  
   - DiT 块：`modules_dit.py` 里 `to_q/k/v/to_out`、`ff.net_0/net_2` 仍是普通 `lin(x)` 调用 → 走 `FP8Linear.forward`

2. **量化层（通用）**  
   - `mlc_vla/quantization/fp8.py` → `FP8Linear.forward`：
     ```text
     x_q = _q(x, self.input_scale, zp, e4m3)   # ← relax.op.quantize
     → _fp8_gemm(x_q, w_fp8, ...)
     ```
   - `_q` ≈ `relax.op.quantize`（同文件顶部薄包装）  
   - **每个 FP8 Linear 入口一次激活 Q** → TVM CUDA codegen 落到 **`quantize1_kernel`**（及融合变体名）

3. **图融合后的变体名（nsys 已见）**  
   - `quantize1_kernel`（独立）  
   - `fused_transpose3_reshape9_quantize_kernel`  
   - `fused_layer_norm_quantize_kernel`  
   → 仍是「算子链末尾的 quantize」，不是 epilogue 内融合；**税仍在**

4. **不是** UniRT runtime 自己插的；UniRT 只加载已编好的 Relax VM。也**不是** synapsex 插的（synapsex 当前负责 FP8 **GEMM** so）。

### 与 π0.5 的对比要点

| | GR00T 现状 | π0.5 已做 |
|---|---|---|
| 权重 | 静态 B（`emit_fp8_gemm`） | 同 |
| 激活 Q | **每 Linear 入口** `FP8Linear.forward` → standalone Q | 上游 fused 核直接出 e4m3 → **`forward_prequantized`**（跳过 Q） |
| AdaLN / Norm | `AdaLayerNorm` / `LayerNorm` 出 fp16，再进 Linear 才 Q | `ada_rms_fp8` / `gated_res_ada_rms_fp8` 出 e4m3 |
| FFN | `net_0 → gelu → net_2`，两端各 Q | `geglu_fp8(merged) → down.forward_prequantized` |

---

## 2. π0.5 如何杀掉独立 Q — 可复用清单（路径）

### 2.1 已在 mlc-vla、可直接复用的 **API / 模式**

| 能力 | 路径 | 用途 |
|---|---|---|
| `FP8Linear.forward_prequantized` | `mlc-vla/.../quantization/fp8.py` | 激活已是 e4m3 时跳过 `_q` |
| `flashrt.geglu_fp8` / `geglu_fp8_supported` | `mlc-vla/.../kernels/flashrt/__init__.py` + shim | GeGLU+Q 合成（π0.5 MLP） |
| `flashrt.gelu_fp8` | `kernels/flashrt/gelu_fp8.cuh` + `__init__.py` | **ViT 已用**：`fc1 → gelu_fp8 → fc2.forward_prequantized` — **与 GR00T FFN（Linear→GELU→Linear）同构，优先复用** |
| `flashrt.ada_rms_fp8` / `gated_res_ada_rms_fp8` | `kernels/flashrt/norm_dps.cuh` + `__init__.py` | adaRMS→e4m3；GR00T 是 **AdaLayerNorm（scale/shift，非 RMS）** → **不能原样套**，只借「norm 出口直接 e4m3」模式 |
| `flashrt.quantize_fp8` | `kernels/flashrt/quantize_fp8.cuh` | 半精度 attn 出 → Q → `o_proj.forward_prequantized`（π0.5 F2d） |
| `flashrt.layer_norm_fp8` | `kernels/flashrt/layer_norm_fp8.cuh` | LN→e4m3；可能贴近 `norm3` / 非-ada 路径 |
| 接线范例 | `model/pi0/gemma_dual.py`（`_geglu_fp8_down`、`_decode_e1_fused`） | **模式参考**；不要把 pi0 文件拷进 GR00T |
| ViT 范例 | `model/pi0/siglip.py`（gelu_fp8 + prequant） | GR00T FFN 最近邻参考 |
| 笔记 | `projects/pi05_optimize/notes/0011-fused-mlp-gegluq.md`、`0015-denoise-adarms-fp8.md` | 收益账本 / 验收口径 |

### 2.2 synapsex 里已有、相关但 **不是 DiT glue**

| 产物 | 路径 | 边界 |
|---|---|---|
| FP8 GEMM unified so | `synapsex/operators/fp8_gemm/` → `libsynapsex_fp8_gemm_unified.so`（现 `libtvm_fp8_gemm_unified.so` 别名） | **已在用**；继续只做 GEMM/epi |
| GU⊕GeGLU epilogue | `operators/fp8_gemm/fp8_geglu_epi_sm100.cuh` | π0.5 **merged gate_up** 专用；GR00T FFN 是 **分两刀 Linear+GELU**，不硬套 |
| 契约 | `synapsex/CONTRACT.md`、`AGENTS.md` | 「通用算子 / 不绑模型名」 |

### 2.3 明确 **不可** 直接复用

- `ada_rms_fp8` 内核公式（RMS + 3 段 modulation）≠ GR00T `AdaLayerNorm`（`silu(temb)→Linear→scale/shift` + affine-free LN）  
- π0.5 `gemma_dual.py` 层间 `(res, delta)` 协议 — DiT 残差形状/门控不同  
- FlashRT 上游整树（交付算子应落 synapsex 或现有 mlc-vla `kernels/flashrt`；新核优先 synapsex）

---

## 3. 推荐分阶段方案（A → B → C）

### Phase A — **优先：复用现有 fused 出 e4m3 + `forward_prequantized`**（mlc-vla 图改，零/少新核）

目标：先砍掉 **FFN 的 `net_2` 入口 Q** 与 **能接到的 to_out / 部分 QKV 入口 Q**。

| 步 | 做什么 | 落点 |
|---|---|---|
| A1 | `FeedForwardGEGLUApprox.forward`：`net_0(x)` → **`flashrt.gelu_fp8(h, net_2.input_scale)`** → `net_2.forward_prequantized`（对标 siglip） | **仅** `modules_dit.py` + 开关（如 `MLC_VLA_GR00T_FFN_GELU_FP8`） |
| A2 | Attn：`to_out` 前若 out 仍 half，试 `quantize_fp8` + `to_out.forward_prequantized`（对标 π0.5 F2d）；或 pack 核直出 e4m3（若已有） | `modules_dit.py` `_attention` |
| A3 | `norm3`（LayerNorm）：评估 `layer_norm_fp8` → 下游 `ff` 入口 prequant；需 shape/dtype 探针 | 同上 |
| A4 | nsys 验收：`quantize*` pct、denoise_step ms；对拍（可后置精度门） | `full_dit_speed_diag` 同口径 |

**预期**：FFN 占原 GEMM 大头之一；A1 单独就可能吃掉可观 Q 次数（每层 1 次 `net_2` Q ×32）。

### Phase B — **AdaLN / 共享激活 Q 合并**（仍偏 mlc-vla 接线；缺核再开 C）

| 步 | 做什么 |
|---|---|
| B1 | 设计 **`ada_ln_fp8`（通用）**：输入 `(x, temb_or_scale_shift, input_scale)` → e4m3；**公式对齐 GR00T AdaLN**，但 API **不出现** `gr00t` / `dit` 字样 |
| B2 | `BasicTransformerBlock`：`norm1` 出口 e4m3 → `to_q/k/v.forward_prequantized`（三路共享同一 `x_q`，π0.5 QKV 共享模式） |
| B3 | 若暂无新核：可 **临时** `flashrt.quantize_fp8(normed, scale)`（仍有一发 Q，但合并三发→一发）；完整消税等 C1 |

### Phase C — **新核进 synapsex**（仅通用算子）

仅当 A/B 探针证明「缺通用原语」时：

| 候选 so / 符号（建议） | 为何进 synapsex | 不进 synapsex |
|---|---|---|
| `ada_ln_to_e4m3`（或扩展现有 norm 族） | 任意 AdaLN-style scale/shift→e4m3 | DiT block 调度、temb 编码 |
| 可选：把 `gelu_fp8` 从 mlc-vla `kernels/flashrt` **上收**到 synapsex（若要多消费者） | 通用 gelu→e4m3 | GR00T `FeedForward` 类 |
| 可选：GEMM epilogue 内 quant（少见） | 挂 `fp8_gemm` epi 扩展 | 模型名 |

构建：`synapsex/scripts/build_*.sh`；契约先改 `CONTRACT.md`；mlc-vla shim `dlsym`（与 fa4/fp4/rope 同模式）。

---

## 4. 模块边界（硬规则）

| 仓 / 组件 | **允许** | **禁止** |
|---|---|---|
| **mlc-vla** | `modules_dit.py` 接线；preset/开关；调用 `flashrt.*` / `forward_prequantized`；GR00T 专用 fallback | 在 synapsex 里写 DiT block |
| **UniRT** | `unirt.tools.pack` 原样打包；runtime env（`LD_PRELOAD` FP8 so） | 改 VM 插 quantize |
| **synapsex** | 通用 CUDA：`fp8_gemm`（已有）、未来 `gelu→e4m3` / `ada_ln→e4m3` 等 **无模型名** API | `gr00t_*`、`dit_block_*`、对拍 yaml、forge 配方 |
| **tvm-relax** | 若需 BYOC/白名单小改（少见） | 业务融合逻辑 |
| **projects/gr00t\*** | bench / nsys / 门禁脚本 | 算子实现 |

原则（摘自 `synapsex/AGENTS.md`）：**算子与模型解耦**；配方与对拍留在 `projects/*`。

---

## 5. 预期收益（基于已测 full_dit）

| 口径 | 数 |
|---|---|
| 现状 lock-freq loop | FP16 76.9 → full **65.2 ms（1.18×）** |
| 现状 nsys step | 18.89 → **15.73 ms（1.20×）**；quantize **2.39 ms（15.2%）** |
| **税=0 上界** | 15.73−2.39=**13.34 ms → 1.42×** vs FP16 |
| Phase A 粗估 | 先消 FFN/`to_out` 相关 Q（未必 100% 税）→ 朝 **1.25–1.35×** 移动 |
| Phase B+C 做完 | 逼近 **~1.4×** step；再清残留 `nvjet_192×8` 等 FP16 GEMM 才可能更高 |
| 精度 | 本计划 **不**绑定 32/32；全量已知 ~25/32，融合后需重跑门禁 |

---

## 6. 建议落地顺序（仍不实施，仅排期）

1. **探针**：在 full_dit 图上数「每步 quantize 实例 / 归属 Linear」（nsys name + IR dump）— 确认税主要在 FFN 还是 AdaLN/QKV。  
2. **Phase A1**（`gelu_fp8` + `net_2.forward_prequantized`）— 最大复用、边界最干净。  
3. 同会话 lock-freq + nsys：看 `quantize_pct` 与 loop×。  
4. 再开 A2/B；缺核再 **CONTRACT → synapsex → shim → modules_dit**。  
5. 精度门另 milestone（覆盖策略 vs 融合可拆开排期）。

---

## 7. 一句话

π0.5 的可复用核心是 **`forward_prequantized` + 上游 fused 出 e4m3`**（尤其 **`gelu_fp8` 已贴合 GR00T FFN**）；AdaLN 需新通用核或临时单次 Q。**接线在 mlc-vla/GR00T，新核只进 synapsex 通用层**；消税后 full_dit 数学上可从 **~1.18× → ~1.42×**。


## 附录：gelu_fp8 已上收 synapsex（2026-10-14）

- **synapsex** 分支 `feat/gelu-fp8-op` @ LT5 `/home/nio/codes/ai_infra/r-infra/synapsex`
  - `operators/gelu_fp8/`（`synapsex_gelu_fp8` + 别名 `flashrt_gelu_fp8`）
  - so：`libsynapsex_gelu_fp8.so`；构建：`GPU_ARCH=110 ./scripts/build_gelu_fp8.sh`（Thor / 含 cuda_fp8 的环境）
  - 测试：`./scripts/run_gelu_fp8_tests.sh`（Thor correctness PASS）
- **mlc-vla** 分支 `feat/gelu-fp8-synapsex`：`gelu_fp8.cuh` 优先 `dlsym` synapsex；`MLC_VLA_GELU_FP8=0` 回落本地核
- **未 push**（Hill：勿推 github；synapsex 仅公司 gitlab）
- Phase A 接线：**已做**（见下节「附录：Phase A 接线」）


## 附录：Phase A 接线（2026-10-14 ~19:50 CST）

- **仓**：LT5 `/home/nio/codes/ai_infra/r-infra/mlc-vla` 分支 `feat/gelu-fp8-synapsex` @ `9bc6084`（gelu uplift 已本地 commit）
- **改动文件（仅此）**：`python/mlc_vla/model/gr00t_n17/modules_dit.py`
- **未 commit / 未 push**（工作树另有 layout/mask 等 WIP；Phase A 与之一并脏，不单独 commit）
- **synapsex**：未改（Phase A 只接线）

### A1 — FFN（必做，已做）

- `FeedForwardGEGLUApprox.forward`：`net_0(x)` → 若开关开且 `net_2` 为 FP8Linear：
  `flashrt.gelu_fp8(h, net_2.input_scale)` → `net_2.forward_prequantized(...)`
- 否则回落：`op.gelu(h)` → `net_2(h)`
- 开关：`MLC_VLA_GR00T_FFN_GELU_FP8` **默认开**；`=0/false/off` 关

### A2 — attn `to_out`（同 pass，已做）

- `BasicTransformerBlock._to_out_maybe_prequant`：half out → `flashrt.quantize_fp8` + `to_out.forward_prequantized`
- layout 核路径与 reshape 回落路径均走该 helper
- 开关：`MLC_VLA_GR00T_ATTN_OUT_FP8` **默认开**；`=0` 关
- 条件：`out` fp16、`numel%8==0`、`to_out.emit_fp8_gemm`（`quantize_fp8_supported`）

### A3 — norm3 / `layer_norm_fp8`（跳过，follow-up）

- DiT 主路径 `norm_type=ada_norm` → `norm3` **`elementwise_affine=False`**（无 γ/β）
- `flashrt.layer_norm_fp8` 需要 weight/bias → **不安全硬套**；留给 Phase B / 探针

### 启用 / 回落

| env | 默认 | 作用 |
|---|---|---|
| `MLC_VLA_GR00T_FFN_GELU_FP8` | ON | A1 FFN gelu_fp8+prequant |
| `MLC_VLA_GR00T_ATTN_OUT_FP8` | ON | A2 to_out quantize_fp8+prequant |
| `MLC_VLA_GELU_FP8` | ON | synapsex so vs 本地 `.cuh`（既有） |

图侧还需 **full_dit（或含 `ff.net_2` / `to_out` 的 FP8 preset）** 把 Linear 换成 `FP8Linear`；否则 helper 条件不满足，静默回落旧路径。

### 校验

- `py_compile` + AST parse：**OK**（LT5 宿主机无 `/opt/r-lib` tvm，未做 `import mlc_vla`）
- Thor 重编 + 锁频/nsys：**已完成**（见「附录：Phase A4 验收」）

### A4（next）— Thor 锁频 + nsys

同口径 `full_dit_speed_diag`：看 `quantize*` pct 与 denoise/loop×。

**Thor（tz-2239 / `pi05-forge-agent`）**：

1. 同步 mlc-vla `feat/gelu-fp8-synapsex` 脏树中的 `modules_dit.py`（+ 确保 `libsynapsex_gelu_fp8.so` 可 `dlsym`，或依赖本地 `.cuh`）
2. 重跑（Thor 上；脚本 LT5 副本 `shared/gr00t-fp8/run_full_dit_fp8_speed_diag.sh`，workdir `/work/gr00t_fp8_phase_a`）：
   ```bash
   # Thor: sync modules_dit.py into compile PYTHONPATH tree, then
   bash run_full_dit_fp8_speed_diag.sh   # preset=e4m3_gr00t_dit；对照 FP16 temb_fix
   ```
3. 关注：`quantize*` ms/%（基线 full_dit **2.39 ms / 15.2%**）、loop×（基线 **1.18×**）、`analyze_full_dit_speed.py` 报告
4. 产物：Thor `/work/gr00t_fp8_phase_a/full_dit_speed_diag/`；回拷 LT5 `shared/gr00t-fp8/expand_bench/full_dit_speed_report.json`

回落对照：`MLC_VLA_GR00T_FFN_GELU_FP8=0 MLC_VLA_GR00T_ATTN_OUT_FP8=0` 重编同 preset，确认加速来自 Phase A。


## 附录：Phase A4 验收（2026-10-14 ~19:56 CST）

- **结果**：A1/A2 **已进图**（nsys 见 `synapsex::gelu_fp8`×384、`quantize_fp8_fp16`×384）
- **quantize 税**：15.21%（2.39 ms）→ **12.29%（1.87 ms）**
- **loop×**：~1.18× → ~1.17×（墙钟未明显抬；nsys GPU 1.20×→1.26×）
- **硬依赖**：Thor forge 编译需 `MLC_VLA_FLASHRT_ROOT=/srcs/data/FlashRT`（`/srcs/FlashRT` 空挂载）
- **残留税**：`quantize1_kernel` ~9%（Phase B AdaLN/QKV 共享 Q）
- 详情见 `gr00t-fp8-status.md` Phase A4 节；报告 JSON 见 `expand_bench/full_dit_phase_a_speed_report.json`


## 附录：Phase B3 临时共享 QKV（2026-10-14 ~20:07 CST）

- **文件**：`modules_dit.py`（`_qkv_from_shared` / `_kv_from_shared` / `_lin_prequant_or_fwd`）
- **开关**：`MLC_VLA_GR00T_QKV_SHARED_FP8` 默认 ON
- **行为**：self 块一发 `quantize_fp8`→三路 prequant；cross 块 Q 单路 + encoder 上 K/V 共享
- **Thor 验收**：quantize **12.3%→3.0%**（0.42 ms）；loop **1.17×→1.28×**；`quantize1` 消失
- **未**做 synapsex `ada_ln`；未 commit/push
- 详见 status「Phase B3」节


## 附录：清 fused_layer_norm_quantize（2026-10-14 ~20:26 CST）

- **根因**：`norm3 → ff.net_0` 的 TVM `fused_layer_norm_quantize`（非 AdaLN）
- **修法**：`layer_norm_fp8`（affine-free 用 ones/zeros）+ `ff.forward_from_prequant`；开关 `MLC_VLA_GR00T_FFN_LN_FP8`
- **验收**：quantize **3.0%→2.2%**；该核消失，见 `layer_norm_fp8_kernel_f16`×384
- 未 commit/push


## 附录：ada_ln_fp8 设计（2026-10-14，设计 only）

完整设计见 **`/workspace/gr00t-ada-ln-fp8-design.md`**（LT5 `shared/gr00t-fp8/` 副本）。

- 通用核：`e4m3(LN_affine_free(x)*(1+scale)+shift)/act_scale`；ABI `synapsex_ada_ln_fp8`
- **不**收 temb/Linear；**无** gr00t/dit 名
- 替换 B3：AdaLN 出口直接 e4m3 → QKV prequant（跳过 shared `quantize_fp8`）
- 本轮 **未实现** / 未改 CONTRACT 正文

### ada_ln_fp8 落地（2026-10-14）

已按设计实现：synapsex `libsynapsex_ada_ln_fp8.so` + mlc-vla `MLC_VLA_GR00T_ADA_LN_FP8`；详见 `gr00t-fp8-status.md` Phase ada_ln_fp8。
