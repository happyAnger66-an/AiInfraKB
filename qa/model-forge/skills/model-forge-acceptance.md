# Model Forge 验收手册

作者：`agent:QA测试/box`

本文件是 QA 操作说明，不是 Cursor skill。每一轮按下面顺序做。

公网站点：[http://www.xiaoanger.com/kb/aiinfra/](http://www.xiaoanger.com/kb/aiinfra/)（角色目录 `qa/` 目前只进 GitHub，不挂站点）。禁止写入 `/wiki/`。

## 执行前

1. 打开本家族套件（例如 `suites/family-gr00t.yaml`）和它 `extends` 的平台套件 `suites/forge-platform.yaml`。
2. 把本轮要跑的用例清单发给晓安哥，确认范围后再执行。未确认的用例不跑。
3. 只使用测试账号 `qa_e2e` 登录测试栈。**密码勿入库**（口令只存在部署侧 secrets，例如 `deploy/secrets/qa_e2e_*.env`）。
4. 不要用生产 `:8088`。GR00T 测栈入口见本轮 `runs/*/env.md`（套件/skills 只用 `${FORGE_WEB}` 等占位）。

## 继承

- 新家族从 `forge-platform.yaml` 继承平台用例（FP8 极致量化默认、量化流水线默认 compare 等），在 `family-*.yaml` 里用 `inherits:` 指向，不复制断言正文。
- 家族文件只写该家族的环境、路径和差异用例；**不写死内网 IP / 具体 ckpt 绝对路径**（那些只进 `runs/`）。
- `runs/` 里的某一轮结果不自动变成下一轮或下一个家族的规则。

## ISSUE 闭环口径（强制）

Agent / 编译 / 算子修完一件后：

1. 责任方在群里喊 **DONE**（含 commit / 包 pin / 热补是否已撤）。
2. QA **新开一单** 回归（新 alias、新 job id）。
3. **禁止** 对失败 job 点重跑 / 刷同一单（失败现场要留作证据）。
4. 关单证据写进本轮 `runs/*/ISSUES.md`：症状 → 归属 → 关单 job。

## API 建单（G2 SoftAdd 可复用）

不依赖「GR00T 交付」前端菜单。约定（占位；具体值见 `runs/`）：

| 项 | 值 |
|---|---|
| Web | `${FORGE_WEB}`（测栈 web，端口惯例 `:18088`；不是现网 `:8088`） |
| 账号 | `qa_e2e` |
| 模板 | `gr00t_n17_softadd_c1` |
| stages | `calib` → `compile` → `unirt_pack` |
| storage | `gpu4090` |
| checkpoint | `${GR00T_CKPT}` / path-preset（datasets **故意空**） |
| agent claim | `gr00t-test-gpu0` |

步骤：

1. `POST /auth/login`（JSON：`username`/`password`）→ cookie / session。
2. `POST /api/v1/gr00t/job/create`，body 至少含：
   - `alias`（建议 `QA-G2-rN-<slug>`）
   - `template_id=gr00t_n17_softadd_c1`
   - `checkpoint_dir=${GR00T_CKPT}`
   - `stages=["calib","compile","unirt_pack"]`
   - `storage_server=gpu4090`
   - `platform=nvidia_thor`
   - `auto_compare=true`（平台默认；本阶段若只验到 pack，compare 可能另开）
3. claim / 盯：`GET /api/v1/gr00t/job/{id}` + `/logs`；列表用 `POST /api/v1/gr00t/job/list`。
4. 验收点：validate/calib/compile/unirt_pack 全绿；日志有正式包 pin；pack 含 `stats.json`（见 G-016）。

详细 payload / 断言见 `skills/gr00t-softadd-api.md`。

## glue 对点（复用 pack）

pack 绿了之后，**不要**重跑 calib/compile。独立对点：

- `POST /api/v1/gr00t/compare/create`
- `job_id=<parent pack job>`（或显式 `apexinfer_model_dir=/data/packs/<alias>`）
- `mode=auto`
- `storage_server=gpu4090`
- golden 约定：`/data/goldens/<parent-alias>/`（首次可走 make_golden；GR00T 也可能 skip make_golden 走 glue）
- 门槛：overall **cos>0.999 ∧ mse<0.0005**；`compare.mode=glue`（平台默认）
- 前置：**G-017** — 测 agent 须挂带 `Gr00tStageMixin` 的 `runner.py`（`_run_gr00t_compare`）
- pack 路径须在 **claim 机（thor）可见**（**G-018**）；否则无 cos/mse

若 compare 失败：记 ISSUE、**新开**回归单，勿刷失败 compare job。

## API ≠ UI（缺口）

- API 绿 **只**盖住 service + agent 链路。
- Web 前端（入口可见 → 建单页 → 列表/详情/日志/产物）须测栈 **web 镜像含 GR00T 入口**后再记 **UI 冒烟** 用例，与 API 分开关单。
- 现网 `:8088` 本来就没有 GR00T 入口；不要拿现网当测栈。

## 每一轮

1. 在 `runs/` 下新建 `YYYY-MM-DD-slug/`（见 `runs/README.md`）。
2. 抄进本轮锁定的端口、提交、套件版本和结果（**含具体 IP/ckpt**）。
3. 跑完后写最终报告。报告里用一张问题表，至少包含：用例 id、现象、是否阻断、责任方、状态。
4. 问题留在该轮目录的 `ISSUES.md`，不把密钥、token 或生产凭据写进仓库。
