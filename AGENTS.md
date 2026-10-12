# AiInfraKB 使用说明（给 agent）

## 查知识

先读 `out/INDEX.md`（运行 `python3 tools/kb.py build --out out` 生成），按硬件、模型、技巧找到卡片 id，再打开 `cards/` 下对应文件。只信 `status: active` 的卡片；`needs-review` 的卡片要自己复验后再用。

## 写知识

1. 从 `templates/` 复制对应类型的模板，放进 `inbox/`，不要直接写进 `cards/`。
2. `claim` 必须带数字或明确条件；`applies_to` 只能用 `vocab/` 里的词，缺词先在词表里加。
3. 证据放 `evidence/<id>/`，在 frontmatter 的 `evidence[].ref` 里引用。
4. 运行 `python3 tools/kb.py lint`，零错误再提交。

## 改这个仓库的代码

- 先写测试，经人 review 后再实现。
- 测试在 `tests/`，用 `python3 -m pytest tests/` 运行。
- 卡片格式变化要同步改 `schema/card.schema.json`、`templates/` 和 `docs/architecture.md`。
