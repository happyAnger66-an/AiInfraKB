# AiInfraKB 使用说明（给 agent）

## 查知识

先运行 `kb query --hardware <硬件> --model <模型> --json`（根目录用 `AIINFRAKB_ROOT` 或 `--root`）。只信 `status: active` 的结果；`warning: true` 的是 `needs-review`，要自己复验后再用。需要全文时再 `kb show <id>`。

## 写知识

1. 从 `templates/` 复制对应类型的模板，放进 `inbox/`，不要直接写进 `cards/`。
2. `claim` 必须带数字或明确条件；`applies_to` 只能用 `vocab/` 里的词，缺词先在词表里加。
3. 证据放 `evidence/<id>/`，在 frontmatter 的 `evidence[].ref` 里引用。
4. 运行 `python3 tools/kb.py lint`，零错误再提交。

## 改这个仓库的代码

- 先写测试，经人 review 后再实现。
- 测试在 `tests/`，用 `python3 -m pytest tests/` 运行。
- 卡片格式变化要同步改 `schema/card.schema.json`、`templates/` 和 `docs/architecture.md`。

## 多机协作与治理

### 写入路径
- 各机上的 bot 可直接 push 到 `main` 的 `inbox/`。
- **禁止**未经批准直接改 `cards/`、`archive/`、`vocab/`、`schema/`。
- 晋升到 `cards/`：治理 bot（New Bot）审核并给出意见；**由人类批准后**再搬迁。

### author 命名
- Agent 写入必须用：`agent:<bot名>/<机器标识>`
- 人类写入用：`human:<名字>`
- 例：`agent:New-Bot/laptop-a`

### 评审节奏
- 治理 bot 定期扫 `inbox/`，按 lint、词表、证据、claim 数字给出通过/修改建议。
- `needs-review`、过期 `review_by`、feedback 失败项一并报告给人。
