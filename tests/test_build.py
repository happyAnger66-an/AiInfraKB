import json

import pytest

import kb
from conftest import make_meta


def build(fixture, tmp_path, **kwargs):
    out = tmp_path / "out"
    kb.build(kb.load_kb(fixture.root), out, **kwargs)
    return out


def all_text(out):
    return "\n".join(p.read_text(encoding="utf-8") for p in out.rglob("*") if p.is_file())


def test_build_refuses_lint_errors(kb_root, tmp_path):
    kb_root.add_card(make_meta(confidence="inferred"))
    with pytest.raises(kb.LintError) as exc:
        build(kb_root, tmp_path)
    assert [i.code for i in exc.value.issues] == ["E_ACTIVE_EVIDENCE"]
    assert not (tmp_path / "out").exists()


def test_build_empty_kb(kb_root, tmp_path):
    out = build(kb_root, tmp_path)
    assert (out / "wiki" / "mkdocs.yml").is_file()
    assert json.loads((out / "html" / "index.json").read_text())["items"] == []
    assert (out / "INDEX.md").is_file()


def test_wiki_card_page(kb_root, tmp_path):
    kb_root.add_card()
    out = build(kb_root, tmp_path)
    mkdocs = (out / "wiki" / "mkdocs.yml").read_text(encoding="utf-8")
    assert "AiInfraKB" in mkdocs
    page = (out / "wiki" / "docs" / "cards" / "kb-0001.md").read_text(encoding="utf-8")
    assert "示例：某算子在 FP8 下保持 FP16" in page
    assert "active" in page
    assert "measured" in page
    assert "2026-10-10" in page
    assert "## 结论" in page
    assert "!!! warning" not in page


@pytest.mark.parametrize("status", ["needs-review", "deprecated"])
def test_wiki_banner_for_non_active(kb_root, tmp_path, status):
    kb_root.add_card(make_meta(status=status))
    out = build(kb_root, tmp_path)
    page = (out / "wiki" / "docs" / "cards" / "kb-0001.md").read_text(encoding="utf-8")
    assert "!!! warning" in page


def test_wiki_includes_archived_card(kb_root, tmp_path):
    kb_root.add_card(make_meta(status="deprecated"), rel_path="archive/lessons/kb-0001.md")
    out = build(kb_root, tmp_path)
    assert (out / "wiki" / "docs" / "cards" / "kb-0001.md").is_file()


@pytest.mark.parametrize(
    "rel",
    ["by-hardware/thor.md", "by-model/pi05.md", "by-technique/fp8-quant.md"],
)
def test_wiki_dimension_pages(kb_root, tmp_path, rel):
    kb_root.add_card()
    out = build(kb_root, tmp_path)
    assert "kb-0001" in (out / "wiki" / "docs" / rel).read_text(encoding="utf-8")


def test_wiki_overview_counts(kb_root, tmp_path):
    kb_root.add_card()
    kb_root.add_card(make_meta(id="kb-0002", status="draft"))
    out = build(kb_root, tmp_path)
    index = (out / "wiki" / "docs" / "index.md").read_text(encoding="utf-8")
    assert "kb-0001" in index and "kb-0002" in index


def test_html_index_json(kb_root, tmp_path):
    kb_root.add_card()
    out = build(kb_root, tmp_path)
    data = json.loads((out / "html" / "index.json").read_text(encoding="utf-8"))
    assert {"title", "description", "items"} <= data.keys()
    (item,) = data["items"]
    assert item["id"] == "kb-0001"
    assert item["title"] == "示例：某算子在 FP8 下保持 FP16"
    assert item["summary"].startswith("示例：误差升高 4 倍")
    assert item["date"] == "2026-10-10"
    assert item["url"] == "/kb/aiinfra/cards/kb-0001/"
    assert item["status"] == "active"
    assert item["type"] == "lesson"
    assert {"thor", "pi05", "fp8-quant", "lesson"} <= set(item["tags"])
    html = (out / "html" / "index.html").read_text(encoding="utf-8")
    assert "index.json" in html


def test_agent_index_only_active(kb_root, tmp_path):
    kb_root.add_card()
    kb_root.add_card(make_meta(id="kb-0002", status="draft"))
    kb_root.add_card(make_meta(id="kb-0003", status="deprecated"))
    out = build(kb_root, tmp_path)
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "kb-0001" in index
    assert "kb-0002" not in index
    assert "kb-0003" not in index


def test_public_only_excludes_private(kb_root, tmp_path):
    kb_root.add_card()
    kb_root.add_card(make_meta(id="kb-0002", visibility="private", title="私有卡片标题"))
    kb_root.add_card(make_meta(id="kb-0003", visibility=None, title="未标注可见性卡片"))
    out = build(kb_root, tmp_path, public_only=True)
    text = all_text(out)
    assert "kb-0001" in text
    for hidden in ("kb-0002", "私有卡片标题", "kb-0003", "未标注可见性卡片"):
        assert hidden not in text


def test_default_build_includes_private(kb_root, tmp_path):
    kb_root.add_card(make_meta(visibility="private"))
    out = build(kb_root, tmp_path)
    assert (out / "wiki" / "docs" / "cards" / "kb-0001.md").is_file()


def test_cli_lint_exit_codes(kb_root):
    kb_root.add_card()
    assert kb.main(["--root", str(kb_root.root), "lint"]) == 0
    kb_root.add_card(make_meta(id="kb-0002", confidence="inferred"))
    assert kb.main(["--root", str(kb_root.root), "lint"]) == 1


def test_cli_build(kb_root, tmp_path):
    kb_root.add_card()
    kb_root.add_card(make_meta(id="kb-0002", visibility="private"))
    out = tmp_path / "cli-out"
    rc = kb.main(["--root", str(kb_root.root), "build", "--out", str(out), "--public-only"])
    assert rc == 0
    assert (out / "wiki" / "docs" / "cards" / "kb-0001.md").is_file()
    assert not (out / "wiki" / "docs" / "cards" / "kb-0002.md").exists()
