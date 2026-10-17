# UI 精度呈现门禁

作者：`agent:知识库/box`（来源：QA测试 G-024 漏测沉淀）

本文件是平台级 QA 看护，不是 Cursor skill。管的是 **呈现**（列表 Tag、compare 详情、键别名），不放宽数字门槛。

配套：`skills/model-forge-acceptance.md`、`skills/test-design.md`、`suites/forge-platform.yaml`（`P-ui-accuracy`、`P-key-alias`、`P-acc-pi05`、`P-acc-overall`）、`suites/family-gr00t.yaml`（`G-acc-dims`）。  
角色目录 `qa/` 目前只进 GitHub，不挂站点。禁止写入 `/wiki/`。

## 背景

G-024：数值精度本身 PASS，UI 打了假黄 Tag。平台读 `overall.cosine`，GR00T glue 产物写的是 `overall.cos`，别名没对上。列表显示 `cosine missing`，详情 overall 指标为空。job 已成功、数字门也过了，单子仍不能关。

正式 SoftAdd 数字门不变：overall **cos>0.999 ∧ mse<0.0005**（平台 `G11`）。本文补 Tag / 详情 / 键别名，以及精度粒度（主表列、`dims[]`）。数字门不改。

测栈入口用 `${FORGE_WEB}`。具体主机、ckpt 只进 `runs/`。

## 规范

### N1 过门≠UI绿

job succeeded，并且数字门 PASS（cos>0.999 ∧ mse<0.0005），仍然不够。必须打开 UI：列表没有假黄 Tag，compare 详情能看到 overall 指标。缺一即 FAIL。

### N2 产物键↔平台键对拍

产物里的指标键必须能别名映射到平台读取的键。例：`cos` ↔ `cosine`（`overall.cos` 须能被读成 `overall.cosine`）。缺别名 = FAIL，即使数字本身已经过门。

### N3 用户路径门禁

关单前走用户能看到的路径：列表 Tag、compare 详情；若该单有 bench，同一 job 的 latency 也要能对上。只看 API 绿不能关单。

### N4 假告警回归

假黄修完后做两步：旧单再灌一次（历史产物不再误报），再新开一单跑一次（新写入带对的键）。不要只刷失败单。

### N5 落盘可继承

本看护落在 `qa/model-forge/`（本 skill + `suites/forge-platform.yaml`），作为可继承的平台规则。家族套件 `extends: forge-platform` 即带上，不在 `family-*.yaml` 里复制断言正文。某一轮 `runs/` 的快照不自动升成规则。

## 和数字门的关系

| 层 | 过关条件 |
|---|---|
| 数字门（G11，不变） | overall cos>0.999 ∧ mse<0.0005 |
| 呈现门（本文 N1–N3） | 无假黄 Tag；详情有 overall 指标；键别名对齐 |
| 粒度（P-acc-* / G-acc-dims） | 主表列齐；overall 字段齐；GR00T `dims[]` 按 pi05 形状呈现。per-dim 不进数字门 |

数字 FAIL 仍按原门处理。数字 PASS 但呈现 FAIL，记 ISSUE，按 `model-forge-acceptance.md` 的新开单口径回归。不放宽 cos/mse。

## 精度粒度（呈现增强）

晓安哥 2026-10-17 确认。在 N1–N5 上把「详情里有什么」写具体，不改 SoftAdd 数字门。

| 用例 | 层 | 断言 |
|---|---|---|
| `P-acc-pi05` | 平台 / 呈现 | 已通过的 pi05 compare 必须在 `${FORGE_WEB}` 展示主精度表：overall 行 + `dims[]` 行；列 `mse \| cosine \| max_abs \| mean_abs \| p90_abs`。缺维表 = FAIL。对标页是成熟的 pi05 用户页 |
| `P-acc-overall` | 平台 / 呈现 | 任意家族的 overall 必须呈现 cosine（含 `cos` 别名双写）+ mse + max_abs + mean_abs；产物里有 p90_abs 则一并呈现。不得假黄 Tag |
| `G-acc-dims` | GR00T / 呈现 | SoftAdd glue 产物写出 pi05 形状的 `dims[]`（逐维 cosine / mse / max_abs / mean_abs，有则 p90_abs）；UI 渲染逐维表。缺维表 = FAIL |
| `P-key-alias` | 平台 / 呈现 | 保持既有 N2：`cos` ↔ `cosine`。不另立别名 |

和 N1–N5：

- N1：数字门 PASS 仍要打开 UI。粒度用例规定主表、列和 `dims[]`，缺一即 FAIL。
- N2 / `P-key-alias`：`cos` ↔ `cosine` 继续有效。`P-acc-overall` 的 cosine 双写就是这条，不新开别名表。
- N3：主表和逐维表走用户路径（列表 Tag、compare 详情）。只看 API 绿不能关单。
- N4：缺表或缺列修完后，旧单复灌一次，再新开一单。不刷失败单。
- N5：`P-acc-*` 写在 `forge-platform.yaml`。GR00T 只在 `family-gr00t.yaml` 写 `G-acc-dims`，并用 `inherits:` 带上 `P-ui-accuracy`、`P-key-alias`、`P-acc-overall`。`P-acc-pi05` 是 pi05 对标页，不抄进家族断言。

平台黄 Tag 仍只读 cosine/cos + mean_abs。overall 上多出来的 mse、max_abs、p90_abs 是呈现字段，不据此打黄 Tag。

逐维只做报告 / 呈现。数字硬门仍只有 overall **cos>0.999 ∧ mse<0.0005**。不要把 per-dim 升成硬门。
