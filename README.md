# AiInfraKB

AI 推理优化知识库，主要给 agent 用：沉淀不同 agent 在不同模型、硬件上做优化时得到的结论、技巧和基线，让新的 agent 会话直接继承。人通过生成的 Wiki 和 HTML 索引查看。

设计说明见 [docs/architecture.md](docs/architecture.md)。

## 目录

| 路径 | 内容 |
|---|---|
| `cards/{facts,lessons,techniques,benchmarks,decisions}/` | 知识卡片，一张卡一个文件，文件名等于 id |
| `archive/<type>s/` | 已废弃或被取代的卡片 |
| `playbooks/` | 把多张卡片串起来的操作手册（如「新模型上 Thor 的优化流程」） |
| `evidence/` | 卡片引用的原始数据、日志、profile 摘要 |
| `inbox/` | agent 提交的候选知识，评审通过才进 `cards/` |
| `templates/` | 5 类卡片模板 |
| `vocab/` | 受控词表：硬件、软件、模型、技巧 |
| `schema/card.schema.json` | 卡片 frontmatter 的 JSON Schema |
| `kb.toml` | TTL、发布配置 |
| `tools/kb.py` | 命令行工具 |
| `tools/kb_mcp.py` | MCP 入口，把工具调用转给 `kb` |

## 用法

```bash
pip install -e ".[dev]" --user --break-system-packages   # 注册 ~/.local/bin/kb，并安装 pytest 与 mcp 1.x
kb lint                          # 校验 cards/ 与 archive/
kb query --hardware thor --model pi05 --json
kb show kb-0001
kb propose --type lesson --title "..." --claim "延迟从 12ms 降到 9ms" \
  --hardware thor --evidence-ref evidence/note.md --author agent:cursor/composer
kb feedback kb-0001 --worked --env thor/trt10.9 --author agent:cursor/composer
kb build --out out               # 生成 out/wiki、out/html、out/INDEX.md
kb build --out out --public-only # 只包含 visibility: public 的卡片
kb-mcp                         # MCP 服务，需 pip install -e ".[mcp]"（锁在 mcp>=1.28,<2）；根目录用 AIINFRAKB_ROOT
python3 -m pytest tests/
```

生成的 Wiki 用 MkDocs 预览：`pip install mkdocs && mkdocs serve -f out/wiki/mkdocs.yml`。

## 状态

P0：仓库框架、schema、词表、模板、`lint`、`build`。P1：`query`、`show`、`propose`、`feedback`、全局命令 `kb`，以及只做转发的 `kb-mcp`。治理扫描在后续阶段加入。
