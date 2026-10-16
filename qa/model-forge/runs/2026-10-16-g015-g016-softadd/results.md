# results — 2026-10-16 SoftAdd G-015/G-016

作者：`agent:QA测试/box`

## 关键刀结论

| 项 | 结果 | 证据 job |
|---|---|---|
| G-015 正式包 SoftAdd dit compile | **PASS**（#19 compile 绿；整单因 G-016 仍红） | `#19` `QA-G2-r11-g015-formal-pack` |
| G-016 pack `stats.json` | **PASS** | `#20` `QA-G2-r12-g016-stats` succeeded ~21m47s |
| SoftAdd API 全流程 calib→compile→pack | **PASS** | `#20` |
| glue 对点（复用 #20 pack） | **FAIL**（Agent 缺 `_run_gr00t_compare`） | `#22` `compare-QA-G2-glue-r1-from20` |
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

## 建单方式

API：`POST /auth/login` + `POST /api/v1/gr00t/job/create`（账号 `qa_e2e`）。不依赖前端「GR00T 交付」页。
