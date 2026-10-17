# UI 精度呈现门禁

作者：`agent:知识库/box`（来源：QA测试 G-024 漏测沉淀）

本文件是平台级 QA 看护，不是 Cursor skill。管的是 **呈现**（列表 Tag、compare 详情、键别名），不放宽数字门槛。

配套：`skills/model-forge-acceptance.md`、`suites/forge-platform.yaml`（用例 `P-ui-accuracy`、`P-key-alias`）。  
角色目录 `qa/` 目前只进 GitHub，不挂站点。禁止写入 `/wiki/`。

## 背景

G-024：数值精度本身 PASS，UI 打了假黄 Tag。平台读 `overall.cosine`，GR00T glue 产物写的是 `overall.cos`，别名没对上。列表显示 `cosine missing`，详情 overall 指标为空。job 已成功、数字门也过了，单子仍不能关。

正式 SoftAdd 数字门不变：overall **cos>0.999 ∧ mse<0.0005**（平台 `G11`）。本文只补 Tag / 详情 / 键别名。

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

数字 FAIL 仍按原门处理。数字 PASS 但呈现 FAIL，记 ISSUE，按 `model-forge-acceptance.md` 的新开单口径回归。不放宽 cos/mse。
