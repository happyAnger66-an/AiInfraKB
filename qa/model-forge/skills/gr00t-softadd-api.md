# GR00T SoftAdd G2 — API 验收菜谱（可复用）

作者：`agent:QA测试/box`  
继承：`suites/forge-platform.yaml` ← `suites/family-gr00t.yaml`  
配套轮次：`runs/2026-10-16-g015-g016-softadd/`

## 测栈约定

| 项 | 约定 |
|---|---|
| Web | `http://10.115.45.181:18088` |
| Service（同源反代亦可） | `:18089` |
| 账号 | `qa_e2e`（**密码不入库**） |
| 模板 | `gr00t_n17_softadd_c1` |
| Agent | `forge-agent-gr00t-test` / claim `gr00t-test-gpu0` |
| storage | `gpu4090`（`/data`） |
| checkpoint | `/data/checkpoints/GR00T-N1.7-3B` |
| datasets | 空（故意） |

## 平台级看护（创建前自检）

- FP8 SoftAdd 模板：极致量化（calib）默认勾且 `requires_calib` 时不可取消 → `forge-platform.G10`
- 量化流水线默认对点：`auto_compare=true` 或 stages 含 compare；`compare.mode=glue`；门槛 cos>0.999 ∧ mse<0.0005 → `forge-platform.G11`

## 建单 payload（最小可复用）

```json
{
  "alias": "QA-G2-rN-<slug>",
  "template_id": "gr00t_n17_softadd_c1",
  "checkpoint_dir": "/data/checkpoints/GR00T-N1.7-3B",
  "stages": ["calib", "compile", "unirt_pack"],
  "platform": "nvidia_thor",
  "storage_server": "gpu4090",
  "calib_samples": 8,
  "auto_compare": true,
  "compare_num_samples": 8,
  "compare_policy_runner": "genie"
}
```

HTTP：

1. `POST /auth/login`
2. `POST /api/v1/gr00t/job/create`（上表 JSON）
3. 盯跑 `GET /api/v1/gr00t/job/{id}`；日志 `GET /api/v1/gr00t/job/{id}/logs`
4. 列表（排查用）`POST /api/v1/gr00t/job/list`

## 分阶段断言

| Stage | PASS 条件 |
|---|---|
| validate | 模板/路径/栈校验通过 |
| calib | 产出 scales（可 cache hit）；SoftAdd C1 `LD_PRELOAD` 钉 `phase_a_so` 的 `libsynapsex_fp8_gemm_c1.so`（本周），非 tip `n3fc2` 残留 |
| compile | bb + dit 均成功；**G-015**：栈含正式包 `mlc-vla-2.0.1-…-ddea2af79`（AdaStatic fold），无依赖测栈热补 `fold_static_adaln_bank` |
| unirt_pack | **G-016**：日志出现「交付补齐 `stats.json` ← checkpoint `statistics.json`」；pack 推到 `gpu4090:/data/packs/<alias>`（含 by_key） |

## glue 对点（pack 之后）

```json
{
  "job_id": 20,
  "alias": "QA-G2-glue-rN-from<parent>",
  "mode": "auto",
  "storage_server": "gpu4090",
  "golden_root": "/data/goldens/<parent-alias>",
  "num_samples": 8,
  "policy_runner": "genie",
  "apexinfer_model_dir": "/data/packs/<parent-alias>",
  "platform": "nvidia_thor"
}
```

`POST /api/v1/gr00t/compare/create`。门槛同平台 G11。

## 热补 vs 正式包（G-015 两层）

| 层 | 含义 | QA 怎么验 |
|---|---|---|
| 热补 | Agent 在测容器打 `fold_static_adaln_bank` / patches 卷，先打通 compile | 可证明「能编」，**不能**关 G-015 |
| 正式包 | service stack pin `mlc-vla-2.0.1-feat_gr00t-adastatic-fold-g015-ddea2af79`；撤热补 | 新开单；日志 `stack_lock` 含该包；compile dit PASS |

## UI 冒烟（另记，勿与 API 混关）

前置：测栈 web 镜像含 GR00T 入口（≥ `b04b877`；换 `:18088` 时勿误伤 service/agent）。

断言：入口可见 → `qa_e2e` 建 SoftAdd 单 → 能看日志/产物。失败则开 UI ISSUE，**新开** UI 单。
