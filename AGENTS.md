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
