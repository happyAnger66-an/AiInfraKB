# DitGemm-Traits — 1SM Traits design / scout（不出代码）

- Date: 2026-10-15T13:20:00+08:00
- Status: **design/scout DONE**；**Verdict = Soft-GO**；**禁出代码 / 禁合基线 / 禁 commit / 禁改 CURRENT**
- Stack lock: L1+L3+LlmRmsQ+EncFp8+D1+crosskv+D1take+AdaStatic+Cg4+LlmSiluEpi+**DitSoftAdd**
- SoftAdd e2e_full **~87.5**；距 66.7 仍约 **20.8 ms**
- Prior: `gr00t-ditgemm-shape.md`（小M税 24.56 ms = 96.6%）、`gr00t-ditgemm-tune.md`（env Tune **NO-GO**）
- Source read-only: `synapsex/operators/fp8_gemm/{fp8_gemm_sm100.cuh,.cu}`；CUTLASS `sm100_umma_builder.inl` / `sm1xx_common.inl` / mainloop+epi `can_implement`

---

## 0. 一句话结论

**Soft-GO。** 根因：现 `Traits1Sm`(128×256×128/1SM) 对 DiT 宽 N 软失败回落 B2，且 `try_1sm` 对 N>1024 **只试这一档、不回落已有 N128/N64**；Gu64 能过但 ff0 更慢。推荐下一实现刀：**先 dispatch 拓宽（复用 N128→N64）探 can_implement**，再上新 **`Traits1SmM64N128`(64×128×128/1SM)**；ROI 上界乐观 −6～−8 ms e2e、现实 −2.5～−5；**默认仍不合** 等测完再批。DitAttnE4 Soft 继续 backlog。

---

## Verdict

| | |
|---|---|
| **设计结论** | **Soft-GO**（值得开一刀实现+measure；非必赢） |
| 推荐首刀 | **C0 dispatch 拓宽**（零新 Traits）→ 若不够再 **C1 `M64N128`** |
| 保持 env | **`TVM_FP8_SMALL_M_TILE=1`**（Tune 已钉） |
| 出代码 / 合基线 | **本刀否**；下一实现刀默认仍 **不合** 等批 |
| DitAttnE4 Soft | **backlog**；勿并行硬啃 |

---

## 1. 根因钉死

### 1.1 现场事实（Tune NO-GO）

| 现象 | 证据 |
|---|---|
| `1sm` 模式仍 672× **B2 256×128 2SM** | nsys `cand_b_1sm`：kern = `SM100_MMA_F8F6F4_2x1SM`，tile 256×128 |
| N∈{1536,6144} 吃不到 1SM | `try_1sm`：N≤256→N64；N≤1024→N128；**更大→`Traits1Sm`** → 软失败 → B2 |
| `GU_TILE` 吃到 ff0 但更慢 | 128×`Gu64x256_1sm`；GEMM +0.51 / loop **+2.14** |
| qkvo/ff2（N=1536） | 不进 `IsGuFp8Shape`(N≥4096)；`1sm` 也失败 |

### 1.2 为何 `Traits1Sm` 对 N=1536/6144 软失败？

**不是**「N 不能被 tileN 整除」：1536%256=0、6144%256=0；K 对 TileK=128 亦可整除。

**不是** TMA 问题尺寸对齐：CUTLASS mainloop/epi `can_implement` 查的是 K/N 对 16B TMA 元素对齐（e4m3→16 elts，half→8 elts）。同 `(M,N,K)=(41,6144,1536)` 的 **`Gu64x256_1sm` 能过**，说明问题尺寸本身可 implement。

**是** 下列叠加（按证据强度）：

1. **分派缺口（硬）**  
   `try_1sm` 对 N>1024 **只试** `Traits1Sm`(128×256×128)，失败即整段 1SM 放弃。  
   **从不**对宽 N 试已编译的 `Traits1SmN128`(128×128×128) / `N64`(128×64×128)。  
   N≤1024 门是 **启发式选 tileN**，不是 CUTLASS 硬限。

2. **`Traits1Sm` 本体软失败（强推断）**  
   Runner 路径：`can_implement` → `workspace` → `initialize`（`CUTLASS_FP8_SM100_TRY`）任一 false 即回落；Tune 统称「can_implement」。  
   同 TileN=256 / 1SM / PerColBias 下 **Gu64(TileM=64) 成功、Traits1Sm(TileM=128) 失败** → 与 **TileM 翻倍带来的 smem / AccumulatorPipeline / epi carveout** 一致：  
   - UMMA builder：1SM×TileM=128×TileN=256 时 Acc stages ≈ `TotalTmem/(128×256)=2`；Gu64 走 MMA_M=64 支路 Acc stages 可达 4。  
   - A+B 每 stage：Traits1Sm ≈48KB vs Gu64 ≈40KB；再加 `PerColLinCombPerColBias` epi SharedStorage + `StageCountAutoCarveout`，Thor optin≥160KB 下 **initialize(`cudaFuncSetAttribute`) 更容易炸**（头文件已有 sm_120 上 can_implement 过但 initialize 失败的先例注释）。  
   - 纯 e4m3×e4m3 **不受** `sm1xx_gemm_check_for_f8f6f4_mix8bit`（仅 unpack F4/F6）编译期否决；故是 **运行时软失败**，不是编不过。

3. **DiT 走 PerColBias epi**（`CutlassFp8GemmRunnerSm100PerCol` / Bias+PerCol），epi smem 大于 plain Identity，进一步压缩 mainloop stages —— 与「大 TileM×大 TileN×1SM」同向加压。

**根因一句话：**  
`try_1sm` 宽 N 只打 `Traits1Sm`(128×256/1SM)，该档在 PerColBias 下对 DiT 形状软失败（对齐无关；同形 Gu64 能过 → 指向 TileM=128×256 1SM 的 smem/initialize），且 **不回落 N128/N64**，故整链回落 B2。

### 1.3 为何 Gu64 能过但更慢？

| | B2 (基线 ff0) | Gu64x256_1sm |
|---|---|---|
| Tile / Cluster | 256×128×**64** / **2SM** | **64**×256×**128** / **1SM** |
| ff0 med | ~57 µs | ~62 µs |
| 128 发 ms | ~7.57 | **8.08**（+0.51） |
| loop 墙钟 | 0 | **+2.14**（含非 GEMM 副作用） |

- **能过：** TileM=64 降 A-tile / 抬 Acc stages，1SM+TileN=256 在 Thor 上可 initialize。  
- **更慢：** 1SM 带宽与调度不如 B2 2SM；TileK=128 vs 64 管线不同；GU µbench (M=50,N=8192,K=1024) −47% **不可外推**到 DiT ff0 (41,6144,1536)。  
- qkvo/ff2 根本不进 GU 门 → 小M税主体未动。

---

## 2. 候选 Traits 菜单

目标 shape：

| 家族 | (M,N,K) | L/loop | ms | 备注 |
|---|---|---:|---:|---|
| qkvo | (41,1536,1536) | 384 | 8.85 | N=K=1536 |
| ff2 | (41,1536,6144) | 128 | 8.21 | N=1536 K=6144 |
| ff0 | (41,6144,1536) | 128 | 7.50 | N=6144 K=1536；GU 已试过更慢 |

Epi：**PerColBias**（DiT Linear）；Cluster 目标：**1SM**（降小 M 上 2SM 浪费）。

| ID | TileShape / Cluster | 适用 | 预计 can_implement | 工程量 | 备注 |
|---|---|---|---|---|---|
| **C0** | **复用** `Traits1SmN128`→`N64`（dispatch only） | 三形 N∈{1536,6144} | **高**（同核已在 N≤1024 跑通；宽 N 仅多 gridY） | **低**：改 `try_1sm` 链，无新 struct | **最低成本探针**；验证「分派缺口」假设 |
| **C1** | **新** `Traits1SmM64N128` = 64×128×128 / 1SM | 三形；门 `M≤64` | **高**（Gu64 证 TileM=64+1SM；N128 证 TileN=128+1SM） | **中**：新 struct + 分派门（`M≤64 && N>1024` 优先） | **主推荐实现刀**；M 浪费 64→41 仅 ~36%（B2 为 84%） |
| **C2** | 扩展 GU 门：现有 `Gu64x256_1sm` 至 N≥1536 | 三形 | **已证**（ff0） | **低**：改 `IsGuFp8Shape` | ff0 **已测更慢** → 默认 **Soft-NO**；除非 qkvo µbench 反转 |
| **C3** | **新** `Traits1SmM64N256K64` = 64×256×64 / 1SM | 偏 ff0/宽 N | **中高** | **中**：新 struct；TileK 对齐 B2 | 对冲 Gu64「TileK=128 过肥」；次于 C1 |
| **C4** | **新** `Traits1SmM32N128` = 32×128×128 / 1SM | 三形 | **中低**（1SM F8 MMA_M 常 64/128；TileM=32 可能编期/软失败） | **中高** | 仅 C1 赢面不足时再探；勿首刀 |

**明确不推荐本轮：**  
- 再扫 env（`1sm`/`GU`/`SKIP_2SM`）— Tune 已 NO-GO。  
- 动 crosskv / QK / SoftAdd / 2-step / Vis*。  
- 抬 `CUTLASS_MIN_M`。  
- 以 `Traits1Sm`(128×256) 原样硬啃 — 已证软失败。

---

## 3. ROI 上界

基准：小M税 **24.56 ms** / e2e gap 至 66.7 ≈ **20.8 ms**；fp8_gemm 占 denoise GPU ~55%。

| 情景 | 假设 | Δ小M税 | 估 Δe2e | 相对「继续 B2」 |
|---|---|---:|---:|---|
| **乐观** | C1 三形均 −30～−35%（M 拟合+1SM 调度赢） | −7.4～−8.6 | **−6～−8.5** | 值得；仍留 gap ~12–15 |
| **现实** | C1 部分形 −10～−20%；或仅 qkvo 有感 | −2.5～−5 | **−2.5～−5** | 边际正；需 same-session 噪声门 |
| **悲观** | 能过但如 Gu64 回归（ff0 已 +0.5 GEMM / +2 loop） | ≥0 | **≥0** | **NO-GO 不合** |
| **理论天花板** | 小M 逼近 M=448 密度（~104 TFLOPS） | ~−20+ | ~−15～−20 | 不现实；1SM Traits 到不了 |
| **继续 B2 不动** | — | 0 | 0 | 零风险零收益；env 已榨干 |

> e2e 不等于 loop：Tune 显示 GU 的 loop 副作用 > GEMM Δ。实现刀必须 **same-session A/B + overall gate**，且以 **e2e_full** 为主判决。

**对比结论：** Traits 是 env 耗尽后唯一合理下一拍；ROI **不足以单刀打到 66.7**，但可能吃掉 gap 的 1/4～1/3（乐观）。不赌天花板。

---

## 4. 推荐下一实现刀（若架构师 GO）

### 4.1 顺序

```
① C0（dispatch only）：try_1sm 宽 N 改为
     Traits1SmN128 → Traits1SmN64 → Traits1Sm → B2
   microbench 三形 can_implement + µs vs B2
   ├─ 若 N128/N64 已明显快 → denoise A/B → gate → 等批（仍默认不合）
   └─ 若能过但不快 / 仍软失败
② C1：加 Traits1SmM64N128 + 门 M≤64∧(N>1024∨强制小M)
   microbench → denoise same-session A/B → overall gate
   └─ 仅当 C1 现实带有赢且稳定，再请批合入；否则 NO-GO 挂 backlog
③ C3 仅作 C1 不足时的宽 N 备选；C2/C4 默认不做
```

### 4.2 验证序（硬）

1. **microbench**：`(41,1536,1536)` / `(41,1536,6144)` / `(41,6144,1536)` + PerColBias；记 can_implement / initialize / med µs / 选中 Traits 名。  
2. **denoise A/B**：SoftAdd pack；`SMALL_M=1` baseline vs cand；lockfreq；warmup=8 iters=40。  
3. **Gate**：overall cos>0.999 ∧ mse<0.0005（期望 bit-identical）。  
4. **nsys**：确认小M 发切到目标 1SM tile，L 仍 672。  
5. **默认不合 / 不 commit / 不改 CURRENT** —— 出数后架构师批。

### 4.3 分派门建议（实现时，本刀不改）

- 保持 `TVM_FP8_SMALL_M_TILE=1` 为现网。  
- 宽 N 小 M：在 B2 之前插入 C0/C1，避免再走「先 B2 成功导致 1SM 永吃不到」（0021 lesson）。  
- GU 门维持 N≥4096 或保持关；**勿**把 C2 当主路径。

---

## 5. 明确不做（本刀 + 下一拍纪律）

| 不做 | 原因 |
|---|---|
| **出生产代码 / 改 synapsex·mlc-vla** | 本刀 design only |
| 合基线 / commit / 改 CURRENT | 未测 |
| 并行硬啃 **DitAttnE4 Soft** | 架构师：backlog 薄利 |
| 再扫现有 env 档 | Tune NO-GO |
| 动 crosskv / QK / SoftAdd / Softmax / PV | 禁区 |
| 2-step / VisNonV1/V1/L2/AttnScore/DitLayout | 禁区 |
| 为 design 重编 so | 本刀只读 |

---

## 6. 群可贴摘要

```
DitGemm-Traits design DONE → Soft-GO（不出代码）
根因：Traits1Sm(128×256/1SM) 对 DiT 宽N软失败回落B2；try_1sm 宽N不回落N128/N64；Gu64能过但ff0更慢
推荐：C0 dispatch拓宽(N128→N64)探针 → C1 新 Traits1SmM64N128(64×128×128/1SM)
ROI上界：乐观 Δe2e −6～−8.5 / 现实 −2.5～−5 / 悲观≥0；吃不完 20.8 gap
下一实现刀默认仍不合；DitAttnE4 Soft backlog
报告: gr00t-ditgemm-traits-design.md
```

---

## 7. Artifacts

| | path |
|---|---|
| 本报告 | `/home/nio/shared/gr00t-fp8/gr00t-ditgemm-traits-design.md` |
| Shape | `gr00t-ditgemm-shape.md` + `ditgemm_shape_hist.json` |
| Tune | `gr00t-ditgemm-tune.md` + `ditgemm_tune_measure_summary.json` |
| Traits 源 | `synapsex/operators/fp8_gemm/fp8_gemm_sm100.{cuh,cu}` |
| CUTLASS | `hpc/cutlass/.../sm100_umma_builder.inl`, `sm1xx_common.inl` |
