import pytest

import kb
from conftest import REPO_ROOT, TYPE_DIRS, make_meta


def codes(root):
    return sorted({issue.code for issue in kb.lint(kb.load_kb(root))})


def test_repo_skeleton_lints_clean():
    assert kb.lint(kb.load_kb(REPO_ROOT)) == []


def test_valid_card_passes(kb_root):
    kb_root.add_card()
    assert codes(kb_root.root) == []


def test_yaml_dates_are_normalized_to_strings(kb_root):
    kb_root.add_card()
    card = kb.load_kb(kb_root.root).cards[0]
    assert card.meta["created"] == "2026-10-01"
    assert card.meta["last_verified"] == "2026-10-10"


def test_card_accessors(kb_root):
    kb_root.add_card()
    card = kb.load_kb(kb_root.root).cards[0]
    assert (card.id, card.type, card.status, card.archived) == (
        "kb-0001",
        "lesson",
        "active",
        False,
    )


@pytest.mark.parametrize("field", ["claim", "applies_to", "confidence", "review_by"])
def test_missing_required_field(kb_root, field):
    kb_root.add_card(make_meta(**{field: None}))
    assert "E_SCHEMA" in codes(kb_root.root)


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "stale"},
        {"type": "tip"},
        {"confidence": "guess"},
        {"visibility": "internal"},
        {"id": "KB-1"},
        {"authors": ["someone"]},
        {"unknown_field": 1},
    ],
)
def test_invalid_values(kb_root, overrides):
    meta = make_meta(**overrides)
    rel = f"cards/lessons/{meta['id']}.md"
    kb_root.add_card(meta, rel_path=rel)
    assert "E_SCHEMA" in codes(kb_root.root)


def test_duplicate_id(kb_root):
    kb_root.add_card()
    kb_root.add_card(make_meta(), rel_path="cards/lessons/sub/kb-0001.md")
    assert "E_DUP_ID" in codes(kb_root.root)


def test_filename_must_equal_id(kb_root):
    kb_root.add_card(rel_path="cards/lessons/fp8-note.md")
    assert "E_FILENAME" in codes(kb_root.root)


def test_type_dir_mismatch(kb_root):
    kb_root.add_card(rel_path="cards/techniques/kb-0001.md")
    assert "E_TYPE_DIR" in codes(kb_root.root)


@pytest.mark.parametrize("status", ["deprecated", "superseded"])
def test_archive_allows_retired_status(kb_root, status):
    kb_root.add_card(make_meta(id="kb-0002"))
    extra = {"superseded_by": "kb-0002"} if status == "superseded" else {}
    kb_root.add_card(make_meta(status=status, **extra), rel_path="archive/lessons/kb-0001.md")
    assert codes(kb_root.root) == []


def test_archive_rejects_active_card(kb_root):
    kb_root.add_card(rel_path="archive/lessons/kb-0001.md")
    assert "E_ARCHIVE_STATUS" in codes(kb_root.root)


@pytest.mark.parametrize(
    "applies_to",
    [
        {"hardware": ["a100x"]},
        {"models": ["unknown-model"]},
        {"techniques": ["magic"]},
        {"software": {"unknown-rt": "1.0"}},
    ],
)
def test_unknown_vocab(kb_root, applies_to):
    kb_root.add_card(make_meta(applies_to=applies_to))
    assert "E_VOCAB" in codes(kb_root.root)


@pytest.mark.parametrize("card_type", ["lesson", "technique", "benchmark"])
def test_claim_requires_number(kb_root, card_type):
    kb_root.add_card(make_meta(type=card_type, claim="示例：开启后明显更快，建议使用"))
    assert "E_CLAIM_NUMBER" in codes(kb_root.root)


@pytest.mark.parametrize("card_type", ["fact", "decision"])
def test_claim_number_not_required(kb_root, card_type):
    kb_root.add_card(make_meta(type=card_type, claim="示例：部署选方案甲而不是方案乙"))
    assert codes(kb_root.root) == []


def test_active_rejects_inferred(kb_root):
    kb_root.add_card(make_meta(confidence="inferred"))
    assert "E_ACTIVE_EVIDENCE" in codes(kb_root.root)


def test_active_rejects_empty_evidence(kb_root):
    kb_root.add_card(make_meta(evidence=[]))
    assert "E_ACTIVE_EVIDENCE" in codes(kb_root.root)


def test_draft_may_be_inferred_without_evidence(kb_root):
    kb_root.add_card(make_meta(status="draft", confidence="inferred", evidence=[]))
    assert codes(kb_root.root) == []


@pytest.mark.parametrize(
    "dates",
    [
        {"review_by": "2026-10-09"},
        {"created": "2026-10-11"},
    ],
)
def test_date_order(kb_root, dates):
    kb_root.add_card(make_meta(**dates))
    assert "E_DATES" in codes(kb_root.root)


@pytest.mark.parametrize(
    "refs",
    [
        {"related": ["kb-0099"]},
        {"supersedes": ["kb-0099"]},
        {"status": "superseded", "superseded_by": "kb-0099"},
    ],
)
def test_unresolved_reference(kb_root, refs):
    kb_root.add_card(make_meta(**refs))
    assert "E_REF" in codes(kb_root.root)


def test_resolved_reference(kb_root):
    kb_root.add_card(make_meta(id="kb-0002"))
    kb_root.add_card(make_meta(related=["kb-0002"]))
    assert codes(kb_root.root) == []


def test_superseded_requires_target(kb_root):
    kb_root.add_card(make_meta(status="superseded"))
    assert "E_SUPERSEDED" in codes(kb_root.root)


def test_missing_local_evidence_file(kb_root):
    kb_root.add_card(with_evidence=False)
    assert "E_EVIDENCE_PATH" in codes(kb_root.root)


def test_url_evidence_not_checked(kb_root):
    ev = [{"kind": "doc", "ref": "https://example.com/spec"}]
    kb_root.add_card(make_meta(evidence=ev), with_evidence=False)
    assert codes(kb_root.root) == []


@pytest.mark.parametrize("section", ["## 结论", "## 适用条件", "## 证据"])
def test_missing_body_section(kb_root, section):
    from conftest import BODY

    kb_root.add_card(body=BODY.replace(section, "## 其他"))
    assert "E_SECTIONS" in codes(kb_root.root)


def test_issue_points_to_card_path(kb_root):
    path = kb_root.add_card(make_meta(confidence="inferred"))
    issues = kb.lint(kb.load_kb(kb_root.root))
    assert [i.path for i in issues] == [path]
    assert issues[0].message


@pytest.mark.parametrize("card_type", sorted(TYPE_DIRS))
def test_templates_have_required_sections(card_type):
    text = (REPO_ROOT / "templates" / f"{card_type}.md").read_text(encoding="utf-8")
    for section in ("## 结论", "## 适用条件", "## 证据"):
        assert section in text
