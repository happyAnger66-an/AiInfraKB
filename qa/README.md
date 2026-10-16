# QA

AiInfraKB 的角色目录：按产品存放验收资产，不进入知识卡片。

| 路径 | 产品 |
|---|---|
| `model-forge/` | Model Forge |

继承顺序：平台套件 ← 家族 overlay ← 单轮 run 快照。平台规则可被家族继承；某一轮的环境与结果只记在 `runs/`，不向上回写。

并行角色以后可以加同级的 `compile/`、`ops/`。公开站点尚未挂出 QA 页面，当前只在 GitHub 阅读这些文件。
