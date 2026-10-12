"""AiInfraKB lint and build."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

TYPE_DIRS = {
    "fact": "facts",
    "lesson": "lessons",
    "technique": "techniques",
    "benchmark": "benchmarks",
    "decision": "decisions",
}
CLAIM_NUMBER_TYPES = {"lesson", "technique", "benchmark"}
ARCHIVE_STATUSES = {"deprecated", "superseded"}
SECTIONS = ("## 结论", "## 适用条件", "## 证据")
DIMENSIONS = (
    ("hardware", "by-hardware"),
    ("models", "by-model"),
    ("techniques", "by-technique"),
)


class LintError(Exception):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__(f"{len(issues)} lint issue(s)")


class Issue:
    def __init__(self, code: str, path: Path, message: str):
        self.code = code
        self.path = path
        self.message = message

    def __repr__(self) -> str:
        return f"Issue({self.code!r}, {self.path!r}, {self.message!r})"


class Card:
    def __init__(self, path: Path, meta: dict, body: str, archived: bool):
        self.path = path
        self.meta = meta
        self.body = body
        self.archived = archived

    @property
    def id(self):
        return self.meta.get("id")

    @property
    def type(self):
        return self.meta.get("type")

    @property
    def status(self):
        return self.meta.get("status")


class KB:
    def __init__(self, root: Path, config: dict, vocab: dict, cards: list[Card], schema: dict):
        self.root = root
        self.config = config
        self.vocab = vocab
        self.cards = cards
        self.schema = schema


def _normalize(value):
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    loaded = yaml.safe_load(parts[1])
    meta = loaded if isinstance(loaded, dict) else {}
    return _normalize(meta), parts[2]


def _parse_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _allowed(vocab: dict, name: str) -> set:
    table = vocab.get(name)
    if isinstance(table, dict):
        return set(table)
    return set()


def load_kb(root) -> KB:
    root = Path(root)
    with (root / "kb.toml").open("rb") as handle:
        config = tomllib.load(handle)
    schema = json.loads((root / "schema" / "card.schema.json").read_text(encoding="utf-8"))
    vocab: dict = {}
    vocab_dir = root / "vocab"
    if vocab_dir.is_dir():
        for path in sorted(vocab_dir.glob("*.yaml")):
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            vocab[path.stem] = loaded if isinstance(loaded, dict) else {}
    cards: list[Card] = []
    for folder, archived in (("cards", False), ("archive", True)):
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
            cards.append(Card(path, meta, body, archived))
    return KB(root, config, vocab, cards, schema)


def _add(issues: list[Issue], code: str, path: Path, message: str) -> None:
    issues.append(Issue(code, path, message))


def lint(kb: KB) -> list[Issue]:
    issues: list[Issue] = []
    validator = Draft202012Validator(kb.schema)
    id_counts = Counter(card.id for card in kb.cards if isinstance(card.id, str))
    known_ids = set(id_counts)

    for card in kb.cards:
        meta = card.meta
        errors = list(validator.iter_errors(meta))
        if errors:
            _add(issues, "E_SCHEMA", card.path, "；".join(error.message for error in errors))

        if isinstance(card.id, str) and id_counts[card.id] > 1:
            _add(issues, "E_DUP_ID", card.path, f"id {card.id} 重复")

        if card.path.stem != card.id:
            _add(issues, "E_FILENAME", card.path, f"文件名 {card.path.stem} 与 id {card.id} 不一致")

        plural = TYPE_DIRS.get(card.type)
        if plural is not None and card.path.parent.name != plural:
            _add(issues, "E_TYPE_DIR", card.path, f"目录应为 {plural}")

        if card.archived and card.status not in ARCHIVE_STATUSES:
            _add(issues, "E_ARCHIVE_STATUS", card.path, "archive/ 中的卡片状态必须是 deprecated 或 superseded")

        applies = meta.get("applies_to")
        if isinstance(applies, dict):
            unknown = False
            for key in ("hardware", "models", "techniques"):
                values = applies.get(key)
                if not isinstance(values, list):
                    continue
                allowed = _allowed(kb.vocab, key)
                if any(value not in allowed for value in values):
                    unknown = True
            software = applies.get("software")
            if isinstance(software, dict) and any(key not in _allowed(kb.vocab, "software") for key in software):
                unknown = True
            if unknown:
                _add(issues, "E_VOCAB", card.path, "applies_to 含有词表之外的名称")

        if card.type in CLAIM_NUMBER_TYPES:
            claim = meta.get("claim")
            if isinstance(claim, str) and re.search(r"\d", claim) is None:
                _add(issues, "E_CLAIM_NUMBER", card.path, "claim 需要包含数字")

        evidence = meta.get("evidence")
        evidence_empty = not isinstance(evidence, list) or len(evidence) == 0
        if card.status == "active" and (evidence_empty or meta.get("confidence") == "inferred"):
            _add(issues, "E_ACTIVE_EVIDENCE", card.path, "active 卡片需要证据，且 confidence 不能是 inferred")

        created = _parse_date(meta.get("created"))
        verified = _parse_date(meta.get("last_verified"))
        review = _parse_date(meta.get("review_by"))
        if created is not None and verified is not None and review is not None:
            if created > verified or review < verified:
                _add(issues, "E_DATES", card.path, "created、last_verified、review_by 顺序不正确")

        missing_ref = False
        for key in ("related", "supersedes"):
            refs = meta.get(key)
            if isinstance(refs, list) and any(ref not in known_ids for ref in refs):
                missing_ref = True
        if "superseded_by" in meta and meta.get("superseded_by") not in known_ids:
            missing_ref = True
        if missing_ref:
            _add(issues, "E_REF", card.path, "引用了不存在的卡片 id")

        if card.status == "superseded" and "superseded_by" not in meta:
            _add(issues, "E_SUPERSEDED", card.path, "superseded 卡片缺少 superseded_by")

        if isinstance(evidence, list):
            missing_file = False
            for item in evidence:
                if not isinstance(item, dict):
                    continue
                ref = item.get("ref")
                if not isinstance(ref, str) or ref.startswith(("http://", "https://")):
                    continue
                if not (kb.root / ref).is_file():
                    missing_file = True
            if missing_file:
                _add(issues, "E_EVIDENCE_PATH", card.path, "证据文件不存在")

        if any(section not in card.body for section in SECTIONS):
            _add(issues, "E_SECTIONS", card.path, "正文缺少结论、适用条件或证据小节")

    return issues


def _publish(kb: KB) -> dict:
    publish = kb.config.get("publish")
    return publish if isinstance(publish, dict) else {}


def _selected(kb: KB, public_only: bool) -> list[Card]:
    if not public_only:
        return list(kb.cards)
    return [card for card in kb.cards if card.meta.get("visibility") == "public"]


def _tags(card: Card) -> list[str]:
    tags: list[str] = []
    if isinstance(card.type, str):
        tags.append(card.type)
    applies = card.meta.get("applies_to")
    if isinstance(applies, dict):
        for key in ("hardware", "models", "techniques"):
            values = applies.get(key)
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, str) and value not in tags:
                    tags.append(value)
    return tags


def _write(path: Path, text: str, written: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    written.append(path)


def _card_page(card: Card) -> str:
    lines = [f"# {card.meta.get('title', '')}", ""]
    if card.status != "active":
        lines.extend(["!!! warning", "", f"当前状态为 {card.status}，引用前请复核。", ""])
    lines.extend(
        [
            f"- status: {card.status}",
            f"- confidence: {card.meta.get('confidence', '')}",
            f"- last_verified: {card.meta.get('last_verified', '')}",
            "",
            card.body.strip(),
            "",
        ]
    )
    return "\n".join(lines)


def _wiki_index(cards: list[Card], site_title: str) -> str:
    type_counts = Counter(card.type for card in cards)
    status_counts = Counter(card.status for card in cards)
    lines = [f"# {site_title}", "", "## 按类型", ""]
    for name, count in sorted(type_counts.items(), key=lambda item: str(item[0])):
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## 按状态", ""])
    for name, count in sorted(status_counts.items(), key=lambda item: str(item[0])):
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## 卡片", ""])
    for card in sorted(cards, key=lambda item: item.id or ""):
        lines.append(f"- {card.id} {card.meta.get('title', '')}")
    lines.append("")
    return "\n".join(lines)


def _agent_index(cards: list[Card]) -> str:
    grouped: dict[str, list[Card]] = {}
    for card in cards:
        if card.status != "active":
            continue
        grouped.setdefault(card.type or "", []).append(card)
    lines = ["# AiInfraKB", ""]
    ordered = [name for name in TYPE_DIRS if name in grouped]
    ordered.extend(sorted(name for name in grouped if name not in TYPE_DIRS))
    for name in ordered:
        lines.extend([f"## {name}", ""])
        for card in sorted(grouped[name], key=lambda item: item.id or ""):
            lines.append(f"- {card.id} {card.meta.get('title', '')}")
        lines.append("")
    return "\n".join(lines)


def _html_page(site_title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>{site_title}</title>
</head>
<body>
  <h1>{site_title}</h1>
  <input id="q" type="search" placeholder="关键字">
  <select id="status">
    <option value="">全部状态</option>
  </select>
  <ul id="items"></ul>
  <script>
    const query = document.getElementById("q");
    const status = document.getElementById("status");
    const list = document.getElementById("items");
    let items = [];

    function render() {{
      const needle = query.value.trim().toLowerCase();
      const wanted = status.value;
      list.replaceChildren();
      items.filter((item) => {{
        const blob = [item.title, item.summary, item.id, ...(item.tags || [])].join(" ").toLowerCase();
        return (!needle || blob.includes(needle)) && (!wanted || item.status === wanted);
      }}).forEach((item) => {{
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.href = item.url;
        link.textContent = item.title;
        li.append(link, ` (${{item.status}})`);
        list.append(li);
      }});
    }}

    fetch("index.json").then((response) => response.json()).then((data) => {{
      items = data.items || [];
      const seen = new Set();
      items.forEach((item) => {{
        if (item.status && !seen.has(item.status)) {{
          seen.add(item.status);
          const option = document.createElement("option");
          option.value = item.status;
          option.textContent = item.status;
          status.append(option);
        }}
      }});
      render();
    }});
    query.addEventListener("input", render);
    status.addEventListener("change", render);
  </script>
</body>
</html>
"""


def build(kb: KB, out, public_only: bool = False) -> list[Path]:
    issues = lint(kb)
    if issues:
        raise LintError(issues)

    out = Path(out)
    cards = _selected(kb, public_only)
    publish = _publish(kb)
    site_title = publish.get("site_title") or "AiInfraKB"
    wiki_base = publish.get("wiki_base_url") or "/wiki/aiinfra-kb/"
    if not str(wiki_base).endswith("/"):
        wiki_base = f"{wiki_base}/"

    written: list[Path] = []
    nav = [{"总览": "index.md"}]
    card_nav = [
        {card.id: f"cards/{card.id}.md"}
        for card in sorted(cards, key=lambda item: item.id or "")
    ]
    if card_nav:
        nav.append({"卡片": card_nav})
    mkdocs = yaml.safe_dump(
        {"site_name": site_title, "docs_dir": "docs", "nav": nav},
        allow_unicode=True,
        sort_keys=False,
    )
    _write(out / "wiki" / "mkdocs.yml", mkdocs, written)
    _write(out / "wiki" / "docs" / "index.md", _wiki_index(cards, site_title), written)

    for card in cards:
        _write(out / "wiki" / "docs" / "cards" / f"{card.id}.md", _card_page(card), written)

    grouped: dict[tuple[str, str], list[Card]] = {}
    for card in cards:
        applies = card.meta.get("applies_to")
        if not isinstance(applies, dict):
            continue
        for key, folder in DIMENSIONS:
            values = applies.get(key)
            if not isinstance(values, list):
                continue
            for name in values:
                if isinstance(name, str):
                    grouped.setdefault((folder, name), []).append(card)
    for (folder, name), group in sorted(grouped.items()):
        lines = [f"# {name}", ""]
        for card in sorted(group, key=lambda item: item.id or ""):
            lines.append(f"- {card.id} {card.meta.get('title', '')}")
        lines.append("")
        _write(out / "wiki" / "docs" / folder / f"{name}.md", "\n".join(lines), written)

    items = []
    for card in sorted(cards, key=lambda item: item.id or ""):
        items.append(
            {
                "id": card.id,
                "title": card.meta.get("title", ""),
                "summary": card.meta.get("claim", ""),
                "tags": _tags(card),
                "date": card.meta.get("last_verified", ""),
                "url": f"{wiki_base}cards/{card.id}/",
                "status": card.status,
                "type": card.type,
            }
        )
    payload = {
        "title": site_title,
        "description": publish.get("description", ""),
        "items": items,
    }
    _write(
        out / "html" / "index.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        written,
    )
    _write(out / "html" / "index.html", _html_page(site_title), written)
    _write(out / "INDEX.md", _agent_index(cards), written)
    return written


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="kb")
    parser.add_argument("--root", default=".", help="知识库根目录")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("lint")
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--out", required=True)
    build_parser.add_argument("--public-only", action="store_true")
    args = parser.parse_args(argv)

    kb = load_kb(args.root)
    if args.command == "lint":
        issues = lint(kb)
        for issue in issues:
            print(f"{issue.code}\t{issue.path}\t{issue.message}", file=sys.stderr)
        return 1 if issues else 0

    try:
        build(kb, args.out, public_only=args.public_only)
    except LintError as exc:
        for issue in exc.issues:
            print(f"{issue.code}\t{issue.path}\t{issue.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
