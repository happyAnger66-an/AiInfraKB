# results — 2026-10-16 SoftAdd G-015/G-016/G-017/G-018

作者：`agent:QA测试/box`

## 关键刀结论

| 项 | 结果 | 证据 job |
|---|---|---|
| G-015 正式包 SoftAdd dit compile | **PASS**（#19 compile 绿；整单因 G-016 仍红） | `#19` `QA-G2-r11-g015-formal-pack` |
| G-016 pack `stats.json` | **PASS** | `#20` `QA-G2-r12-g016-stats` succeeded ~21m47s |
| SoftAdd API 全流程 calib→compile→pack | **PASS** | `#20` |
| G-017 glue 方法（`_run_gr00t_compare`） | **关账**（方法已挂上；`e13199b`） | 暴露 `#22`；smoke hasattr=True |
| glue 对点（复用 #20 pack） | **FAIL** → 见 G-018 | `#22`（缺方法）；`#24`（缺 thor 可见 bb pack） |
| UI 冒烟 | **未测**（web 旧镜像） | — |

## #20 阶段

| stage | status |
|---|---|
| validate | succeeded |
| calib | succeeded（cache hit 可） |
| compile | succeeded（bb+dit；stack 含 `mlc-vla-2.0.1-…-ddea2af79`） |
| unirt_pack | succeeded |

关键日志：

- `交付补齐 stats.json ← checkpoint statistics.json (Isaac-GR00T)`
- pack：`gpu4090:/data/packs/QA-G2-r12-g016-stats` → by_key `2f6af67759ae`

## #19 说明

- validate/calib/compile **succeeded**；unirt_pack **failed**（缺 `stats.json`）→ 整单 `failed`
- 关 **G-015** 看 compile + 正式包 pin；关 **G-016** 看后续新开的 `#20`

## glue 轨迹

| job | alias | 结果 | 说明 |
|---|---|---|---|
| `#22` | `compare-QA-G2-glue-r1-from20` | FAIL | `JobRunner` 无 `_run_gr00t_compare`；make_golden skipped；无 cos/mse → **G-017** |
| `#24` | `compare-QA-G2-glue-r2-g017` | FAIL | 方法已在；thor 不可见 bb pack `/data/packs/QA-G2-r12-g016-stats`；无 cos/mse → **G-018**（勿刷） |

## 建单方式

API：`POST /auth/login` + `POST /api/v1/gr00t/job/create`（账号 `qa_e2e`）。不依赖前端「GR00T 交付」页。具体 `${FORGE_WEB}` / ckpt 见同目录 `env.md`。
