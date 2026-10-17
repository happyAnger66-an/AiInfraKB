# 用例设计

作者：`agent:QA测试/box`

本文件是 QA 怎么设计用例的短说明，不是 Cursor skill。角色目录 `qa/` 目前只进 GitHub，不挂站点。禁止写入 `/wiki/`。

入口用 `${FORGE_WEB}`。内网 IP、主机名、ckpt 绝对路径、口令只进 `runs/`。

## 对标

Oracle 用已经成熟的兄弟家族用户页，不凭空发明表头。精度主表以 pi05 compare 页为准：overall 行 + `dims[]` 行，列 `mse | cosine | max_abs | mean_abs | p90_abs`（`P-acc-pi05`）。后来的家族（例如 GR00T SoftAdd glue）按这个形状补呈现，不另起一套列。

## 分层

一条用例只钉一层：

| 层 | 问什么 | 例 |
|---|---|---|
| hard | 数字门槛过不过 | overall cos>0.999 ∧ mse<0.0005（G11 / G6）。per-dim 不升硬门 |
| presentation | 用户看得见的表、Tag、键是否齐 | `P-acc-pi05`、`P-acc-overall`、`G-acc-dims`、`P-ui-accuracy`、`P-key-alias`（N2：`cos` ↔ `cosine`） |
| path | 用户路径走不走得通 | 列表 Tag → compare 详情；API 绿单独不算关单 |

缺的是某一层，就只改那一层。呈现缺口不改数字门。

## 缺字段是产品缺口

页面或产物少一列、少 `dims[]`、键对不上（例如只写了 `cos`、平台读 `cosine`），记产品缺口。不把缺口写成「这轮先不看」。平台黄 Tag 仍只读 cosine/cos + mean_abs；多出来的列先要求呈现，不据此新打黄 Tag。

缺口收成平台规则，写进 `suites/forge-platform.yaml`。家族套件只写本家族差异：适用的平台用例用 `inherits:` 指向，不复制断言正文。`P-acc-pi05` 是 pi05 对标页，GR00T 用 `G-acc-dims` 要求写出同形 `dims[]`，不把 pi05 建单断言抄进 `family-gr00t.yaml`。

## 确认后再执行

用例 id 和断言写完，先把清单发给晓安哥。确认范围后再跑。未确认的用例不执行。

## `runs/` 与 `suites/`

`suites/` 和 `skills/` 是可继承规则。`runs/YYYY-MM-DD-slug/` 只锁这一轮的环境、数字和问题单，不回写成平台规则，也不自动变成下一个家族的断言。
