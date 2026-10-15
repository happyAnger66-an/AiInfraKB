# model_forge 本机无状态化主线收口 — 证据摘要

来源：2026-10-15 本机 compose 收口；model_forge_web 补清单校对。下表是本卡采用的数字。未在 AiInfraKB 仓库内复跑，也不把提交哈希当成这些计数的证据。

## 范围

主线：web W0–W5、service S1/S2、agent A1–A5。

未做完：尚未真上 lab-ssr 集群；下一真实任务的控制台端到端尚未再盯。本摘要不表示集群已上线。

## 校对数字

| 项 | 记录 |
|---|---|
| 契约 | `model_forge_service/docs/ARTIFACT_CONTRACT.md`。对外 URI 唯一形态 `mfs://artifacts/<key>` |
| W2 | 本机 MySQL。杀掉 web 容器后，账号 **13**、presets **2**、feedback **3** 仍在 |
| S1 | 库名 `model_forge_service`（sqlite→MySQL）。库内 job **112**、logs **86464**、agents **4**。healthz `db_driver=mysql` |
| S2/A5 | job **115** 冒烟 URI `mfs://artifacts/115/a5_smoke.bin`，by-uri **200**。对外 URI 禁止 `/work` 本机路径；单测拒绝把 `/work` 当成对外 URI |
| web 回归 | 覆盖登录、presets、BFF 代理。补清单没有单独的通过条数 |
| agent | `pytest forge_agent` **141 passed**。upload 之后只采用服务端返回的 `mfs://` |

## mfs

`mfs` 是 **Model Forge Storage** 的逻辑名。`mfs://artifacts/<key>` 里的 key 映射到 `PI05_ARTIFACT_ROOT` 下的物理路径。`/work/...` 是本机路径，不是可下载的对外 URI。

## 提交例

只作收口指针，不代替上表计数：

- agent：`b1e6fb5` / `46babfa` / `e91c321` / `87d94b7`
- service：`52a4988` / `29f7b84` / `4a550f1`
- web compose：`a4e8415`

## 边界

领域结论留在 AiInfraKB。仓边界与一刀一功能归 agent-kit（atomic-commit PR），不写入本卡 claim。
