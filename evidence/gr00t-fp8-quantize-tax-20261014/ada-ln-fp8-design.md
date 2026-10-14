# synapsex 通用 `ada_ln → e4m3` 设计（B1 / C 候选）

- 日期：2026-10-14
- 状态：**已实现**（2026-10-14）；synapsex `feat/ada-ln-fp8` + mlc-vla wiring；CONTRACT 已合入 ada_ln_fp8 节；Thor 正确性 PASS；pack/nsys 见 status
- 动机：Phase B3 用 `quantize_fp8(AdaLN 出口)` 把 QKV 入口 Q 三发并一发，仍留 **显式 Q ~2.2%**；完整消税需 **AdaLN 出口直接 e4m3**（π0.5 `ada_rms_fp8` 同模式，公式不同）
- 边界硬规则：synapsex **无** `gr00t` / `dit` 字样；DiT 调度与 `silu(temb)→Linear` 留 mlc-vla

---

## 1. 要对齐的数学（GR00T / diffusers AdaLN）

mlc-vla `AdaLayerNorm`（`modules_dit.py`）：

```text
emb   = Linear(SiLU(temb))          # [B, 2D]，权重在模型侧
scale, shift = split(emb, 2)        # 各 [B, D] → broadcast [B, 1, D]
y     = LN(x; affine=False, eps) * (1 + scale) + shift
# 今日下游：y (fp16) → quantize_fp8(y, to_q.input_scale) → QKV.forward_prequantized  (B3)
```

要点：

| 项 | GR00T AdaLN | π0.5 `ada_rms_fp8`（**不可原样套**） |
|---|---|---|
| 归一化 | **LayerNorm**（减均值 + rsqrt(var+eps)） | **RMSNorm**（无减均值） |
| 仿射 | **无** γ/β（`elementwise_affine=False`） | Gemma `(1+w)` 乘在 RMS 上 |
| modulation | **scale + shift**（2×D，来自 temb MLP） | scale + shift + **gate**（3×D） |
| 出口 | 今日 half；目标 **e4m3 / act_scale** | 已是 e4m3 |

因此需要 **新通用原语**，不是给 `ada_rms_fp8` 换皮。

---

## 2. 推荐 API 切分（v1）

### 2.1 核内只做「已算好的 scale/shift + LN → e4m3」

**不把** `SiLU(temb)→Linear` 收进 synapsex：

- 那是普通 GEMM + 激活，已有 FP8/FP16 路径；塞进 norm 核会绑权重布局与「2×D vs 3×D」模型细节
- 通用消费者（非 DiT）往往 **已经** 有 scale/shift 张量

```text
out_e4m3 = ada_ln_fp8(x, scale, shift, act_scale, eps)
# 等价：
#   n = LN_affine_free(x, eps)
#   y = n * (1 + scale) + shift          # scale/shift broadcast 到 x 的 token 维
#   out = e4m3( clip(y / act_scale, ±448) )
```

### 2.2 命名（无模型名）

| 层 | 建议名 |
|---|---|
| so | `libsynapsex_ada_ln_fp8.so` |
| C++ | `synapsex::ada_ln_fp8::Run` |
| C ABI（权威） | `synapsex_ada_ln_fp8(...)` |
| 图侧 / shim 符号 | `flashrt_ada_ln_fp8`（mlc-vla SourceModule 名；与 gelu 一样「图侧旧名 + so 权威」） |
| mlc-vla Python | `flashrt.ada_ln_fp8` / `ada_ln_fp8_supported` |

**禁止**：`gr00t_*`、`dit_*`、`ada_ln_gr00t_*`。

### 2.3 拟议 C ABI

对齐 `gelu_fp8` 风格（指针 + 几何 + stream；**不**链 libtvm）：

```c
// x, scale, shift: __half*; out: __nv_fp8_e4m3*; d_act_scale: device fp32 scalar
// x:      [rows, dim] 行主连续（rows = B*T 或由调用方拍平）
// scale:  [B, dim] 行主；第 b 行广播到该 batch 的全部 token
// shift:  同 scale
// 若 B==rows（已按 token 展开），则 scale/shift 每行各用一行（亦合法）
extern "C" int synapsex_ada_ln_fp8(
    const void* x,
    const void* scale,
    const void* shift,
    void* out,
    const float* d_act_scale,
    int rows,
    int dim,
    int batch,          /* scale/shift 行数；token 属 batch b = row / (rows/batch) */
    int tokens_per_batch, /* 通常 T；须 rows == batch * tokens_per_batch */
    float eps,
    cudaStream_t stream);
// 返回：0 ok；-1 空指针；-2 几何非法（rows/dim/batch<=0、rows!=batch*tokens、dim%2!=0 等）；
//       -3 dim 超实现上限（与 layer_norm_fp8 / kNormMaxDim 同级，建议 4096）
```

**可选精简重载（若实现只支持 B 维广播）**：固定 `tokens_per_batch = rows/batch`，校验整除即可。

**dtype（v1）**：

| 张量 | dtype |
|---|---|
| x / scale / shift | float16 |
| out | float8_e4m3fn |
| d_act_scale | float32 设备标量（下游 `FP8Linear.input_scale`） |

bf16 / 分段 act_scale：**v1 不做**。

### 2.4 数值细节（实现约束）

- LN：fp32 累加 mean / var；`rsqrtf(var+eps)`；**无** γ/β
- 调制：`y = n * (1 + scale) + shift`（与现图一致；scale/shift 先升 fp32 再算）
- Q：`out = e4m3(fminf(fmaxf(y / *d_act_scale, -448), 448))`；可与 `gelu_fp8` / `layer_norm_fp8` 同 clip
- 向量化：dim 偶数；半维 half2（同现有 norm 族）
- **不要求**与「LN half → quantize_fp8」bit 一致（少一次 half round-trip）；靠对拍门禁（cos/mse）

### 2.5 错误 / supported 门（mlc-vla）

`ada_ln_fp8_supported(x, scale, shift, act_scale)` 建议：

- `flashrt.available()` 且 so/`cuh` 可注册
- x.dtype == scale.dtype == shift.dtype == float16
- act_scale dtype float32、numel==1
- x 最后一维静态 int、`dim%2==0`、`dim <= kNormMaxDim`
- scale/shift 形状为 `[B,1,D]` 或 `[B,D]` 且 D==dim、B==x.shape[0]
- 失败 → 回落今日 `AdaLayerNorm` + B3 `quantize_fp8`

---

## 3. 仓边界

| 组件 | 做 | 不做 |
|---|---|---|
| **synapsex** | `operators/ada_ln_fp8/` 核 + so + correctness/bench；CONTRACT 节；`docs/operators/ada_ln_fp8.json` | temb、SiLU、Linear 权重、DiT block、QKV 调度、标定 |
| **mlc-vla flashrt shim** | `dlsym(synapsex_ada_ln_fp8)`；`ada_ln_fp8` Python；优先 so / `MLC_VLA_ADA_LN_FP8_SO`；可选本地 `.cuh` 回落 | 模型名 API |
| **modules_dit** | `AdaLayerNorm` 仍算 `scale/shift`（或拆 `_modulation(temb)`）；调用 `ada_ln_fp8` 得 `x_q`；QKV `forward_prequantized`；开关 | 把 DiT 类搬进 synapsex |
| **projects / forge** | 锁频 + nsys；精度门 | 算子实现 |

与已上收 `gelu_fp8` 同模式：`GPU_ARCH=110 ./scripts/build_ada_ln_fp8.sh` → `dist/lib/libsynapsex_ada_ln_fp8.so`。

---

## 4. mlc-vla 接线草图（so 落地后）

### 4.1 伪代码（替换 B3 里「AdaLN 后再 Q」）

```python
# AdaLayerNorm：可拆成 modulation + 融合出口
emb = self.linear(op.silu(temb))
scale, shift = op.split(emb, 2, axis=-1)
scale = op.reshape(scale, (B, 1, D))
shift = op.reshape(shift, (B, 1, D))

if env MLC_VLA_GR00T_ADA_LN_FP8 and ada_ln_fp8_supported(...):
    # act_scale = to_q.input_scale（self / cross-Q 共享）
    x_q = flashrt.ada_ln_fp8(x, scale, shift, to_q.input_scale, eps)
    # self: to_q/k/v.forward_prequantized(x_q)
    # cross: to_q.forward_prequantized(x_q)；K/V 仍走 encoder 上 _kv_from_shared
else:
    normed = LN(x) * (1+scale) + shift   # 今日
    # B3 quantize_fp8(normed) ...
```

### 4.2 与 B3 开关关系

| 开关 | 角色 |
|---|---|
| `MLC_VLA_GR00T_QKV_SHARED_FP8` | B3 临时：half AdaLN 后共享 `quantize_fp8` |
| `MLC_VLA_GR00T_ADA_LN_FP8`（新） | 优先：AdaLN→e4m3；**启用时跳过** 对该 `x_q` 的 B3 `quantize_fp8` |
| `MLC_VLA_ADA_LN_FP8_SO` / `SYNAPSEX_HOME` | so 发现（同 gelu） |

Cross 的 **encoder K/V** 不经 AdaLN → **仍**用 B3 `_kv_from_shared`（或未来 encoder 侧原语）；不在本算子范围。

### 4.3 为何不是「包一层 layer_norm_fp8」

`layer_norm_fp8` = `e4m3(LN(x;γ,β)/s)`，**没有** `(1+scale)+shift`。  
若图上先算 `y = LN*(1+s)+h` 再 `quantize_fp8(y)`，仍是 **两段**（或 LN+Q 融核），消不掉今日 `fused_layer_norm_add2_multiply5_add3` + 后续 Q。  
目标核必须 **单发** 含 LN + 调制 + Q。

---

## 5. 验收口径（相对 Phase B3 / B3+LN）

基线（B3+LN_FP8，2026-10-14 Thor）：quantize **2.2%（0.30 ms）**；loop **~1.27×**；显式 `quantize_fp8`×**960**/12iter；AdaLN half 核 `fused_layer_norm_add2_multiply5_add3` ~0.8%。

| 预期变化（ada_ln_fp8 替换「AdaLN half + 其后 Q」） | 说明 |
|---|---|
| `quantize_fp8` launches | 960 → ~**576**（少 32 层 ×12：self 共享 Q + cross-Q） |
| `fused_layer_norm_add2_multiply5_add3` | 每步 ~32 发 **应消失或大幅下降**（折进 ada_ln_fp8） |
| 新核 | `synapsex::ada_ln_fp8` / `ada_ln_fp8_*` ×384（32×12） |
| quantize\* 桶 | 2.2% → 粗估 **~1.3–1.6%**（仍留 to_out Q + cross-KV Q） |
| loop× | 略升可期（消 AdaLN half + 一截 Q）；上界仍受 FP16 GEMM ~20% 限制 |

精度：对拍 denoise（既有门禁）；允许与「half AdaLN + quantize」非 bit 一致。

---

## 6. 实现分期（不在本轮）

| 步 | 内容 |
|---|---|
| C0 | CONTRACT 合入下文「拟增节」+ `operators/ada_ln_fp8/README` |
| C1 | CUDA 核 + `build_ada_ln_fp8.sh` + correctness（CPU 参考 / 金标 half 路径） |
| C2 | mlc-vla shim `dlsym` + `ada_ln_fp8` Python |
| C3 | `modules_dit` 接线 + Thor 锁频/nsys（对照 §5） |
| C4（可选） | 本地 `.cuh` 回落；bf16；或「scale/shift 已是 fp32」变体 |

**不推荐 v1**：核内 SiLU+Linear、gate 段、与 `ada_rms` 强行统一成一核多模式（会糊边界）。

---

## 7. 拟增 CONTRACT 节（实现 PR 粘贴；本轮不改仓内 CONTRACT.md）

```markdown
## ada_ln_fp8

| 项 | 契约 |
|---|---|
| so 文件名 | `libsynapsex_ada_ln_fp8.so` |
| C++ API | `synapsex::ada_ln_fp8::Run` |
| C ABI | `synapsex_ada_ln_fp8(x, scale, shift, out, d_act_scale, rows, dim, batch, tokens_per_batch, eps, stream)` |
| 公式 | `e4m3( (LN_affine_free(x)*(1+scale)+shift) / act_scale )`，clip ±448 |
| 布局 | x `[rows,dim]` half；scale/shift `[batch,dim]` half；out e4m3 同 x；act_scale fp32 标量设备 |
| 图侧符号 | `flashrt_ada_ln_fp8`（shim）；数值优先本 so |
| 链接 | **不**链 libtvm |
| Arch | `GPU_ARCH`（110 Thor / 120 按平台矩阵） |

### 环境变量

| 变量 | 含义 |
|---|---|
| `MLC_VLA_ADA_LN_FP8_SO` | 指向本 so |
| `SYNAPSEX_HOME` | 回落 `dist/lib/libsynapsex_ada_ln_fp8.so` |
| `MLC_VLA_ADA_LN_FP8` | 优先 so（默认开；`0` 可强制本地回落，若有） |
```

---

## 8. 一句话

通用 **`ada_ln_fp8(x, scale, shift, act_scale)`**：仿射无关 LN + `(1+scale)+shift` + 静态 e4m3；**temb/Linear 留 mlc-vla**。落地后替换 B3「AdaLN half + shared quantize_fp8」，可再砍 ~1pp Q 税并吃掉 AdaLN half 核；命名与 gelu_fp8 同契约族，**无模型名**。
