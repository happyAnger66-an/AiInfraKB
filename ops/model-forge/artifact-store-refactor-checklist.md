# ArtifactStore 存储重构 · 改造清单

> **状态**：已批开干——本清单进 AiInfraKB；Agent 按契约开 tip upload PR。  
> **现网冻结**：不改 `PI05_ARTIFACT_ROOT`、不 rsync（「先不动」）；SoftAdd 不合 master / 不发站；测栈不跟。  
> **契约权威**：`model_forge_service/docs/ARTIFACT_CONTRACT.md` @ `8e2c5367ca5ffcb528a2a56d70c91cd929a3f1d8`（2026-10-15）  
> **KB 目标**：`http://www.xiaoanger.com/kb/aiinfra/`（禁止 `/wiki/`）  
> **author**：`agent:知识库/box`  
> **来源**：model_forge_web 交稿（box 草稿脱敏落地；公司仓不上云）

---

## 1. 背景 / 问题

控制面已迁现网 tip，**数据面仍绑某一台机的本地盘**：

| 现象 | 根因 |
|------|------|
| tip 动态调度后产物断链 | job / 下载仍依赖执行机或某台 `storage_server` 本机目录 |
| GR00T `#161/#163` 能下、π0.5 历史单（如 `#152`）404 | 门④只抽了 SoftAdd 绿材料到现网 tip；历史 **`pi05_artifacts`** blob 未迁 |
| 现网 tip Root 误指 `/data/pi05_datasets` | 测栈真值是 `PI05_ARTIFACT_ROOT=/data/pi05_artifacts`（host `${ARTIFACT_HOST_ROOT}/pi05_artifacts`，契约同此）；绿包碰巧落在误配的 `pi05_datasets` / softadd-green 上故能下 |

一句话：**库里有行 ≠ 公共存储上有文件 ≠ UI Tab 非空**。动态调度下三者必须解耦。

> 目录名钉死：**ArtifactRoot = `pi05_artifacts`**（不是 `pi05_jobs`，也不是现网 tip 误指的 `pi05_datasets`）。

---

## 2. 目标与非目标

### 目标（一句话）

**job 表只存契约 URI；所有产物只认公共 ArtifactStore；agent 本地只是缓存。**

### 分层目标

1. **ArtifactStore（数据面）**：单一 `put/get/list`；URI 继续 `mfs://artifacts/{job_id}/…`（远期可 `s3://`）。现网 tip service **只挂 Store**，禁止再绑「本机偶然目录」。
2. **Agent 写路径**：runner 结束 → upload/flush 到 Store → 再写 `artifacts_json` / 状态；tip `/tmp` 可丢。
3. **Web 读路径**：`fetchCompareSummary` / `fetchBenchReport` / 下载 **只解析 URI→Store**，不再猜 `gpu4090` / 主机标签。
4. **材料类**（packs / goldens / checkpoints / calib）：进 Store 或只读材料桶；SoftAdd 重跑不依赖 tip 本地碰巧有文件。
5. **迁移**：现有 `pi05_artifacts` / packs **import→Store**；`storage_server` 字段作废或改 `store=default`。

### 非目标（本轮明确不做）

- [ ] **不改**现网 tip 的 `PI05_ARTIFACT_ROOT`（维持现状，含误指 `pi05_datasets`）
- [ ] **不**全量 / 按需 rsync 测栈 `pi05_artifacts` → 现网 tip（「先不动」）
- [ ] SoftAdd **不合** master、**不发站**
- [ ] 测栈不跟生产切流
- [ ] 不在本轮强制上对象存储驱动（接口预留即可；backend 可先继续用公共盘）

---

## 3. 契约摘要（对齐 ARTIFACT_CONTRACT，勿另立口径）

| 项 | 约定 |
|----|------|
| 唯一对外 URI | `mfs://artifacts/<key>`，`<key>`=`{job_id}/{filename}`（`filepath.Base`，禁穿越） |
| 禁止对外 | `/work/...`、`/home/...`、`/data/jobs/...`、`/data/packs/...`、其它本机绝对路径 |
| 本机后端 | `PI05_ARTIFACT_ROOT/<key>`（契约：现网多为 `/data/pi05_artifacts/<key>`） |
| Agent 登记 | **推荐唯一稳妥**：`PUT /v1/pi05/agent/job/{id}/artifact/upload?name=&stage=` → 内部写 canonical URI |
| 仅登记 | `POST /v1/pi05/agent/job/{id}/artifact` 且文件已在 ArtifactRoot；`downloadable=true` + 执行机路径 → **400** |
| 下载 | `GET /v1/pi05/job/{id}/artifacts/{name}`；`GET /v1/pi05/artifacts/by-uri?uri=mfs://…` |
| Job 视图字段 | `uri`（mfs://…）、`download_url`（BFF 相对路径） |
| 读出 scrub | 历史本地路径 → 对外 `uri` 置空、`downloadable=false`（不改 DB） |
| Agent/Web | **只认** `mfs://artifacts/<key>`；对象存储映射由 Service 解析 |

Service 侧 upload / by-uri / scrub **已就绪**；本轮缺口主要在 **Agent tip 强制 upload** + **Web 读路径去主机猜** + **运维 Store 挂载口径**。

---

## 4. 分角色改造清单

### 4.1 Web（BFF + 前端）— model_forge_web

- [ ] **BFF**：`fetchCompareSummary` / `fetchBenchReport` / 产物下载 **只**走 `by-uri` 或 job `download_url`；删除对 `storage_server` / `gpu4090` / 固定主机路径的猜测
- [ ] **BFF**：解析失败或 404 时明确错误码；不回退到 scp/本机拼路径
- [ ] **前端详情 Tab（精度 / 耗时）**：优先渲染 DB `accuracy_metrics` / duration 等字段作兜底；artifact JSON 作明细（有则展开，无则 Tab 仍可用 metrics）
- [ ] **列表 / 详情**：展示 `uri`（`mfs://…`）与 `downloadable`；不可下载时 UI 明示「产物未入 Store」而非空白
- [ ] **改造清单进 KB**：本文件发布到 AiInfraKB（由知识库执行写入）

**验收**：打开有 metrics 无 blob 的历史单（如 `#152`）→ Tab 有 DB 数字、下载区标明不可下；打开绿 `#161/#163` → by-uri 200 + Tab 明细齐全。

### 4.2 Service（model_forge_service）

- [ ] **固化 Store API**：对外仅 `mfs://`；内部 `put/get/list` 抽象稳定（现网 backend 可仍为盘）
- [ ] **现网 tip 只认 Store**：compose/env 文档标明「唯一 ArtifactRoot / Store 挂载」；禁止再加「偶然 bind」进下载路径
- [ ] **`storage_server` 字段**：新写入废弃或写 `store=default`；读路径忽略主机标签
- [ ] **材料桶**（可选本轮或紧随）：packs/goldens/checkpoints/calib 只读材料 URI 规范（仍不进 job 对外假路径）
- [ ] **契约文档**：若 API 有增补，先改 `ARTIFACT_CONTRACT.md` 再改 Agent/Web

**验收**：带本机绝对路径的 downloadable 登记继续 400；by-uri 只解析 Store；单元/集成覆盖 scrub 与 upload。

### 4.3 Agent（model_forge_agent）— **本轮主 PR**

- [ ] **tip upload 闭环**：runner 成功产物 **只走** `PUT …/artifact/upload`；禁止把 `/work/jobs/...` 填进 `uri`
- [ ] **done 门禁**：关键产物 upload 成功后才标 job done / 写终态（对齐 QA：upload 成功才 done）
- [ ] **读父任务产物**：用 `download_url` 或 `by-uri`；本机缓存可用，但不得作为唯一来源（禁兄弟机 scp 当真相源）
- [ ] **日志 vs 对外**：日志可打本机路径；`artifacts_json` 对外字段 **只用** `mfs://`
- [ ] **scratch**：tip `/tmp`（或等价）可随时丢；重跑不依赖 tip 本地残留

**验收**：任意 tip 跑完 → Store 上有 blob + DB `artifacts[].uri` 均为 `mfs://artifacts/{id}/…`；杀 tip 本地目录后 by-uri 仍 200。

### 4.4 运维

- [ ] **文档化现网真相**：测栈 Root=`/data/pi05_artifacts`（host `${ARTIFACT_HOST_ROOT}/pi05_artifacts`）；现网 tip 现误指 `/data/pi05_datasets`；绿 `#161/#163` 另落 softadd-green / datasets（**本轮不改指针**）
- [ ] **Store 挂载规范**（重构落地时）：现网 tip service **只**挂公共 Store 卷；禁「某台偶然目录」
- [ ] **历史 import 预案**（另批再执行）：测栈 `pi05_artifacts` / packs → Store；**不在「先不动」期内执行 rsync**
- [ ] **改 Root 护栏**（若将来改 env→`pi05_artifacts`）：必须同时迁或软链 `#161/#163`（及约定 packs/scales），禁止只改指针导致绿详情瞬间 404

**验收**：有书面 runbook；任何改 Root 变更单附带绿目录迁/链检查项。

---

## 5. 四步落地顺序与依赖

| 步 | 内容 | 依赖 | 谁 | 现网「先不动」下 |
|----|------|------|-----|------------------|
| ① | 固化 Store API + 现网 tip 只认 Store（文档/代码口径） | 契约已有 | Service + 运维文档 | **可做**（不改现网 env 指针） |
| ② | tip 上传闭环（强制 upload → 再 done） | ① API 稳定 | **Agent PR** | **可做**（写路径走 upload，落现有 Root） |
| ③ | 灌历史 blob（`pi05_artifacts` import / rsync → Store） | ①；需另批 | 运维 | **冻结**（先不动） |
| ④ | 去掉主机标签（`storage_server` 作废；Web 去猜主机） | ② 为主；③ 补齐体验 | Web + Service | **可做代码**；全量体验等 ③ |

推荐并行：② Agent PR ∥ Web 读路径改造（4.1）∥ 本清单进 KB。③ 等单独批示。

---

## 6. QA 验收门（重构结案）

结案须 **三者齐**：

1. job 行有 metrics（DB）
2. 公共存储上 artifact 可读（`mfs://` → Store，HTTP 200）
3. UI Tab 非空（DB 兜底 + 有产物时明细）

| # | 门 | 通过标准 |
|---|-----|----------|
| Q1 | upload 成功才 done | 未 upload 不得终态成功；失败可观测 |
| Q2 | 对外只认 `mfs://` | 抽样 artifacts_json 无本机绝对路径；旧脏数据对外 scrub |
| Q3 | tip scratch 可扔 | 清空 tip 工作目录后 by-uri / 详情仍可用 |
| Q4 | 详情 Tab | DB metrics 兜底 + 产物明细；无 blob 不空白崩 |
| Q5 | 绿回归 | `#161/#163` compare/bench/glue 仍 200（改 Root 前必测） |

QA 先交用例版给确认后再测，不抢跑。

---

## 7. 风险与护栏

| 风险 | 影响 | 护栏 |
|------|------|------|
| 只把现网 tip Root 改成 `/data/pi05_artifacts` 却未迁/链仍在 `pi05_datasets`（及 softadd-green）的绿 `#161/#163` | 绿详情立刻 404 | **先不动**；若将来改 env：必须迁/链绿目录 + packs/scales |
| 历史 `pi05_artifacts` blob 未灌 | `#152` 等继续 404 | 接受至另批 ③；UI 用 DB 兜底降低「假空」 |
| Agent 仍写本机 uri | 动态 tip 断链复发 | PR 门禁：upload-only + CI 拒绝对路径 |
| Web 仍猜主机 | 调度后读失败 | BFF 只认 URI→Store |
| SoftAdd / 发站误跟 | 不合规合入 | SoftAdd 不合 master、不发站；测栈不跟 |
| 目录名再混用 `pi05_jobs` | 运维/文档跑偏 | 只认契约与测栈：`pi05_artifacts` |

---

## 8. 开干回执（本批）

| 项 | 状态 |
|----|------|
| 本改造清单 → AiInfraKB `/kb/aiinfra/` 树（角色目录 `ops/`） | 本 PR；站点挂 `ops/` 为后续，卡片上站另批 |
| Agent tip upload PR（按 ARTIFACT_CONTRACT） | 待 model_forge_agent 开 PR |
| 现网 env / rsync | **先不动**（已批） |
| 历史灌盘 / 改 Root | 另批；附绿目录护栏 |
| 公司仓上云 | **禁止** |

**修订**：改契约先改 `ARTIFACT_CONTRACT.md`，再改本清单与各仓。
