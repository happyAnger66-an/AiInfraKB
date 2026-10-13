# AiInfraKB 架构

AiInfraKB 是给 agent 用的 AI 推理优化知识库：每条知识是一张卡片，写明结论、适用条件和证据；人看的 Wiki 和 HTML 索引都从卡片生成。

## 数据流

```mermaid
flowchart LR
  subgraph repo["AiInfraKB 仓库"]
    CFG["kb.toml<br/>TTL、发布配置"]
    SCH["schema/card.schema.json"]
    VOC["vocab/*.yaml<br/>受控词表"]
    CARDS["cards/&lt;type&gt;s/*.md<br/>archive/&lt;type&gt;s/*.md"]
    EVI["evidence/"]
  end
  CFG --> LOAD["load_kb"]
  SCH --> LOAD
  VOC --> LOAD
  CARDS --> LOAD
  LOAD --> LINT["lint<br/>格式 / 词表 / 引用 / 证据 / 日期"]
  EVI --> LINT
  LINT -->|有错误| STOP["退出码 1，不构建"]
  LINT -->|通过| BUILD["build"]
  BUILD --> WIKI["out/wiki/<br/>mkdocs.yml + docs/"]
  BUILD --> HTML["out/html/<br/>index.html + index.json"]
  BUILD --> AIDX["out/INDEX.md<br/>只含 active，给 agent"]
```

`query`、`show`、`propose`、`feedback` 和 `lint`、`build` 用同一个 `KB` 对象，不改卡片格式。治理扫描（P2）以后也加在这里。

## 类图

```mermaid
classDiagram
  class KB {
    +Path root
    +dict config
    +dict vocab
    +list~Card~ cards
  }
  class Card {
    +Path path
    +dict meta
    +str body
    +id() str
    +type() str
    +status() str
    +archived() bool
  }
  class Issue {
    +str code
    +Path path
    +str message
  }
  class LintError {
    +list~Issue~ issues
  }
  KB "1" *-- "many" Card
  LintError o-- Issue

  class kb_module {
    <<module tools/kb.py>>
    +load_kb(root) KB
    +lint(kb) list~Issue~
    +build(kb, out, public_only=False) list~Path~
    +query(kb, hardware, model, technique, text) list~Hit~
    +show(kb, card_id) str
    +propose(kb, ...) Path
    +feedback(kb, card_id, ...) Path
    +main(argv) int
  }
  class Hit {
    +Card card
    +int score
    +bool warning
  }
  class ProposeError
  class FeedbackError
  kb_module ..> KB
  kb_module ..> Issue
  kb_module ..> LintError
  kb_module ..> Hit
  kb_module ..> ProposeError
  kb_module ..> FeedbackError
```

- `load_kb` 读取 `cards/` 和 `archive/` 下的所有 `.md`，把 YAML 解析出的日期统一转成 `YYYY-MM-DD` 字符串后再交给 schema 校验。
- `build` 先调用 `lint`，有任何 `Issue` 就抛出 `LintError`。
- `public_only=True` 时，`visibility` 不是 `public` 的卡片不出现在任何产物里。

## agent 命令

根目录用 `--root`，否则用环境变量 `AIINFRAKB_ROOT`，都没有则用当前目录。`pyproject.toml` 把 `kb` 注册为控制台命令，入口是 `kb:main`（`main` 不传参数时读取 `sys.argv`）。

| 命令 | 行为 |
|---|---|
| `kb query` | 返回未归档、状态为 `active` 或 `needs-review` 的卡片。`--hardware`、`--model`、`--technique` 必须同时满足；`--text` 在标题、claim、正文里做不区分大小写的子串匹配。`needs-review` 的 `Hit.warning` 为真。排序：`reproduced` > `measured` > `inferred`，相同置信度时 `last_verified` 更新的在前，再按 id。`--json` 打印数组，每项含 `id`、`status`、`claim`、`warning`、`score` |
| `kb show <id>` | 打印该卡片文件原文。找不到时抛 `NotFoundError`，命令退出码 2 |
| `kb propose` | 在 `cards/`、`archive/`、`inbox/` 里取最大编号加一，把草稿写入 `inbox/<id>.md`，不改 `cards/`。必填 type、title、claim、至少一项 `applies_to`、至少一条已存在的证据路径、`agent:` 或 `human:` 开头的 author。`lesson` / `technique` / `benchmark` 的 claim 必须有数字，词表外的名字拒绝。失败抛 `ProposeError` 且不写文件。`status` 为 `draft`，`created` 与 `last_verified` 为当天，`review_by` 为当天加 `kb.toml` 里该类型的 TTL |
| `kb feedback <id> --worked\|--failed` | 向 `feedback/<id>.jsonl` 追加一行，字段为 `id`、`result`、`env`、`author`、`note`、`at`。不修改卡片。id 不存在或 result 非法时抛 `FeedbackError` 且不写文件 |

## lint 规则

| 代码 | 规则 |
|---|---|
| `E_SCHEMA` | frontmatter 不满足 `schema/card.schema.json`（缺字段、枚举值错、格式错） |
| `E_DUP_ID` | 卡片 id 重复 |
| `E_FILENAME` | 文件名（不含 `.md`）不等于 id |
| `E_TYPE_DIR` | 所在目录不是 `<type>s/`（如 `lesson` 必须在 `lessons/`） |
| `E_ARCHIVE_STATUS` | `archive/` 下的卡片状态不是 `deprecated` 或 `superseded` |
| `E_VOCAB` | `applies_to` 里的硬件、软件、模型、技巧不在词表中 |
| `E_CLAIM_NUMBER` | `lesson`、`technique`、`benchmark` 的 `claim` 里没有数字 |
| `E_ACTIVE_EVIDENCE` | `active` 卡片没有证据，或置信度是 `inferred` |
| `E_DATES` | `created` 晚于 `last_verified`，或 `review_by` 早于 `last_verified` |
| `E_REF` | `related`、`supersedes`、`superseded_by` 指向不存在的 id |
| `E_SUPERSEDED` | `superseded` 状态缺少 `superseded_by` |
| `E_EVIDENCE_PATH` | 证据 `ref` 是仓库内路径但文件不存在（`http(s)://` 链接不检查） |
| `E_SECTIONS` | 正文缺少 `## 结论`、`## 适用条件`、`## 证据` 任一节 |

## build 产物

| 路径 | 内容 |
|---|---|
| `out/wiki/mkdocs.yml` | MkDocs 配置，站点名取 `kb.toml` 的 `publish.site_title` |
| `out/wiki/docs/index.md` | 总览：按类型、状态计数 |
| `out/wiki/docs/cards/<id>.md` | 每张卡一页；顶部写状态、置信度、最后验证日期；非 `active` 状态加 `!!! warning` 横幅 |
| `out/wiki/docs/by-hardware/<name>.md`、`by-model/`、`by-technique/` | 按维度列出卡片 |
| `out/html/index.json` | 门户兼容格式：`title`、`description`、`items[]`，每项含 `id`、`title`、`summary`（claim）、`tags`、`date`（last_verified）、`url`（`publish.wiki_base_url` + `cards/<id>/`）、`status`、`type` |
| `out/html/index.html` | 单页索引，读取 `index.json`，可按关键字和状态过滤 |
| `out/INDEX.md` | 给 agent 的精简目录，只列 `active` 卡片，按类型分组 |
