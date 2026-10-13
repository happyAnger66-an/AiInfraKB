import datetime as dt
import json

import pytest

import kb
from conftest import REPO_ROOT, make_meta


def test_package_registers_kb_command():
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'kb = "kb:main"' in text


def test_query_returns_active_and_marks_needs_review(kb_root):
    kb_root.add_card()
    kb_root.add_card(make_meta(id="kb-0002", status="needs-review", title="待复验的示例卡片标题"))
    kb_root.add_card(make_meta(id="kb-0003", status="draft"))
    kb_root.add_card(make_meta(id="kb-0004", status="deprecated"))
    kb_root.add_card(
        make_meta(id="kb-0005", status="deprecated"),
        rel_path="archive/lessons/kb-0005.md",
    )
    loaded = kb.load_kb(kb_root.root)
    hits = kb.query(loaded)
    by_id = {hit.card.id: hit for hit in hits}
    assert set(by_id) == {"kb-0001", "kb-0002"}
    assert by_id["kb-0001"].warning is False
    assert by_id["kb-0002"].warning is True


def test_query_filters_are_combined(kb_root):
    kb_root.add_card()
    other = make_meta(id="kb-0002", title="另一条硬件上的示例")
    other["applies_to"] = {"hardware": ["orin"], "models": ["pi05"]}
    kb_root.add_card(other)
    loaded = kb.load_kb(kb_root.root)
    hits = kb.query(loaded, hardware="thor", model="pi05", technique="fp8-quant", text="误差")
    assert [hit.card.id for hit in hits] == ["kb-0001"]
    assert kb.query(loaded, text="不存在的句子") == []


def test_query_ranks_confidence_then_recency(kb_root):
    older = make_meta(
        id="kb-0001",
        confidence="reproduced",
        last_verified="2026-01-01",
        review_by="2026-07-01",
    )
    newer = make_meta(
        id="kb-0002",
        confidence="measured",
        last_verified="2026-10-01",
        review_by="2027-04-01",
    )
    same = make_meta(
        id="kb-0003",
        confidence="reproduced",
        last_verified="2026-06-01",
        review_by="2026-12-01",
    )
    kb_root.add_card(older)
    kb_root.add_card(newer)
    kb_root.add_card(same)
    loaded = kb.load_kb(kb_root.root)
    hits = kb.query(loaded)
    assert [hit.card.id for hit in hits] == ["kb-0003", "kb-0001", "kb-0002"]
    assert hits[0].score > hits[2].score


def test_query_includes_private_cards(kb_root):
    kb_root.add_card(make_meta(visibility="private"))
    hits = kb.query(kb.load_kb(kb_root.root))
    assert [hit.card.id for hit in hits] == ["kb-0001"]


def test_show_returns_file_text(kb_root):
    path = kb_root.add_card()
    loaded = kb.load_kb(kb_root.root)
    assert kb.show(loaded, "kb-0001") == path.read_text(encoding="utf-8")


def test_show_missing_card(kb_root):
    with pytest.raises(kb.NotFoundError):
        kb.show(kb.load_kb(kb_root.root), "kb-0099")


def test_cli_query_json_and_show(kb_root, capsys):
    kb_root.add_card()
    root = str(kb_root.root)
    assert kb.main(["--root", root, "query", "--hardware", "thor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["id"] == "kb-0001"
    assert payload[0]["claim"].startswith("示例：误差升高 4 倍")
    assert payload[0]["warning"] is False
    assert "score" in payload[0]
    assert kb.main(["--root", root, "show", "kb-0001"]) == 0
    assert "kb-0001" in capsys.readouterr().out
    assert kb.main(["--root", root, "show", "kb-0099"]) == 2


def test_cli_root_from_env(kb_root, capsys, monkeypatch):
    kb_root.add_card()
    monkeypatch.setenv("AIINFRAKB_ROOT", str(kb_root.root))
    assert kb.main(["query", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["id"] == "kb-0001"


def _evidence(kb_root, ref="evidence/note.md"):
    path = kb_root.root / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("raw\n", encoding="utf-8")
    return ref


def test_propose_writes_draft_inbox_and_passes_lint(kb_root):
    kb_root.add_card()
    ref = _evidence(kb_root)
    loaded = kb.load_kb(kb_root.root)
    path = kb.propose(
        loaded,
        type="lesson",
        title="示例：新的踩坑记录",
        claim="延迟从 12ms 降到 9ms",
        applies_to={"hardware": ["thor"], "models": ["pi05"]},
        evidence_refs=[ref],
        author="agent:cursor/composer",
        today=dt.date(2026, 10, 1),
    )
    assert path == kb_root.root / "inbox" / "kb-0002.md"
    assert not (kb_root.root / "cards" / "lessons" / "kb-0002.md").exists()
    text = path.read_text(encoding="utf-8")
    assert "status: draft" in text
    assert "review_by: 2027-03-30" in text
    reloaded = kb.load_kb(kb_root.root)
    assert kb.lint(reloaded) == []
    assert kb.show(reloaded, "kb-0002") == text


@pytest.mark.parametrize(
    "kwargs",
    [
        {"claim": "开启后明显更快建议使用"},
        {"applies_to": {"hardware": ["a100x"]}},
        {"evidence_refs": []},
        {"author": "cursor"},
        {"evidence_refs": ["evidence/missing.md"]},
    ],
)
def test_propose_rejects_invalid_input(kb_root, kwargs):
    ref = _evidence(kb_root)
    base = dict(
        type="lesson",
        title="示例：会被拒绝的卡片",
        claim="延迟从 12ms 降到 9ms",
        applies_to={"hardware": ["thor"]},
        evidence_refs=[ref],
        author="agent:test",
        today=dt.date(2026, 10, 1),
    )
    base.update(kwargs)
    with pytest.raises(kb.ProposeError):
        kb.propose(kb.load_kb(kb_root.root), **base)
    assert list((kb_root.root / "inbox").glob("*.md")) == [] if (kb_root.root / "inbox").exists() else True


def test_propose_id_skips_archive_and_inbox(kb_root):
    kb_root.add_card(make_meta(id="kb-0002", status="deprecated"), rel_path="archive/lessons/kb-0002.md")
    inbox = kb_root.root / "inbox"
    inbox.mkdir()
    (inbox / "kb-0004.md").write_text("placeholder\n", encoding="utf-8")
    ref = _evidence(kb_root)
    path = kb.propose(
        kb.load_kb(kb_root.root),
        type="fact",
        title="示例：一条硬件事实",
        claim="该硬件有 20 个 SM",
        applies_to={"hardware": ["thor"]},
        evidence_refs=[ref],
        author="human:xiaoan",
        today=dt.date(2026, 1, 1),
    )
    assert path.name == "kb-0005.md"


def test_feedback_appends_jsonl_without_editing_card(kb_root):
    card = kb_root.add_card()
    before = card.read_text(encoding="utf-8")
    loaded = kb.load_kb(kb_root.root)
    path = kb.feedback(
        loaded,
        "kb-0001",
        result="worked",
        env="thor/trt10.9",
        author="agent:cursor/composer",
        note="这次有效",
        at="2026-10-13T00:00:00Z",
    )
    kb.feedback(
        loaded,
        "kb-0001",
        result="failed",
        env="orin/trt10.9",
        author="agent:claude/opus",
        at="2026-10-14T00:00:00Z",
    )
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert path == kb_root.root / "feedback" / "kb-0001.jsonl"
    assert rows[0] == {
        "id": "kb-0001",
        "result": "worked",
        "env": "thor/trt10.9",
        "author": "agent:cursor/composer",
        "note": "这次有效",
        "at": "2026-10-13T00:00:00Z",
    }
    assert rows[1]["result"] == "failed"
    assert rows[1]["note"] == ""
    assert card.read_text(encoding="utf-8") == before


def test_feedback_rejects_unknown_card_and_bad_author(kb_root):
    kb_root.add_card()
    loaded = kb.load_kb(kb_root.root)
    with pytest.raises(kb.FeedbackError):
        kb.feedback(loaded, "kb-0099", result="worked", env="thor", author="agent:test")
    with pytest.raises(kb.FeedbackError):
        kb.feedback(loaded, "kb-0001", result="worked", env="thor", author="someone")
    assert not (kb_root.root / "feedback").exists()


def test_cli_propose_and_feedback(kb_root, capsys):
    kb_root.add_card()
    ref = _evidence(kb_root, "evidence/kb-new/run.md")
    root = str(kb_root.root)
    rc = kb.main(
        [
            "--root",
            root,
            "propose",
            "--type",
            "technique",
            "--title",
            "示例：开启 cuda graph",
            "--claim",
            "单步延迟从 12ms 降到 9ms",
            "--hardware",
            "thor",
            "--model",
            "pi05",
            "--evidence-ref",
            ref,
            "--author",
            "agent:test",
            "--today",
            "2026-10-01",
        ]
    )
    assert rc == 0
    assert "inbox/kb-0002.md" in capsys.readouterr().out
    assert kb.main(
        [
            "--root",
            root,
            "feedback",
            "kb-0001",
            "--failed",
            "--env",
            "thor/trt10.9",
            "--author",
            "agent:test",
            "--at",
            "2026-10-13T00:00:00Z",
        ]
    ) == 0
    row = json.loads((kb_root.root / "feedback" / "kb-0001.jsonl").read_text(encoding="utf-8"))
    assert row["result"] == "failed"
