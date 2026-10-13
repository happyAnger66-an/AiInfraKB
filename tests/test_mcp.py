import asyncio

import pytest

import kb_mcp
from conftest import REPO_ROOT


def test_package_registers_kb_mcp_command():
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'kb-mcp = "kb_mcp:main"' in text


def test_mcp_dependency_pinned_below_v2():
    pin = "mcp>=1.28,<2"
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert pin in pyproject
    assert pin in requirements


def test_server_does_not_import_kb_module():
    text = (REPO_ROOT / "tools" / "kb_mcp.py").read_text(encoding="utf-8")
    assert "import kb" not in text
    assert "from kb" not in text


def test_command_adds_root_only_when_set():
    assert kb_mcp.command(None, ["lint"]) == ["kb", "lint"]
    assert kb_mcp.command("/tmp/kb", ["show", "kb-0001"]) == [
        "kb",
        "--root",
        "/tmp/kb",
        "show",
        "kb-0001",
    ]


def test_query_args_always_json_and_skips_empty_filters():
    assert kb_mcp.query_args(hardware="thor", model=None, technique="", text="误差") == [
        "query",
        "--json",
        "--hardware",
        "thor",
        "--text",
        "误差",
    ]


def test_propose_and_feedback_args_match_cli():
    assert kb_mcp.propose_args(
        type="lesson",
        title="示例标题",
        claim="延迟从 12ms 降到 9ms",
        hardware=["thor"],
        model=["pi05"],
        technique=[],
        evidence_ref=["evidence/note.md"],
        author="agent:test",
        today="2026-10-01",
    ) == [
        "propose",
        "--type",
        "lesson",
        "--title",
        "示例标题",
        "--claim",
        "延迟从 12ms 降到 9ms",
        "--hardware",
        "thor",
        "--model",
        "pi05",
        "--evidence-ref",
        "evidence/note.md",
        "--author",
        "agent:test",
        "--today",
        "2026-10-01",
    ]
    assert kb_mcp.feedback_args(
        "kb-0001",
        result="failed",
        env="thor/trt10.9",
        author="agent:test",
        note="",
        at=None,
    ) == [
        "feedback",
        "kb-0001",
        "--failed",
        "--env",
        "thor/trt10.9",
        "--author",
        "agent:test",
    ]


class _Proc:
    def __init__(self, code, out, err):
        self.returncode = code
        self.stdout = out
        self.stderr = err


def test_forward_returns_stdout_unchanged():
    raw = '[{"id": "kb-0001"}]\n'

    def run(argv, capture_output, text):
        assert argv == ["kb", "--root", "/tmp/kb", "query", "--json"]
        assert capture_output is True and text is True
        return _Proc(0, raw, "")

    assert kb_mcp.forward("/tmp/kb", ["query", "--json"], run=run) == raw


def test_forward_raises_with_stderr_on_failure():
    def run(argv, capture_output, text):
        return _Proc(2, "", "kb-0099\n")

    with pytest.raises(kb_mcp.KbMcpError) as exc:
        kb_mcp.forward(None, ["show", "kb-0099"], run=run)
    assert exc.value.returncode == 2
    assert str(exc.value) == "kb-0099\n"


def _call(server, name, arguments):
    result = asyncio.run(server.call_tool(name, arguments))
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, str):
        return result
    return "".join(block.text for block in result)


def test_tools_only_forward(monkeypatch):
    seen = []

    def fake(root, args, run=None):
        seen.append((root, args))
        return "RAW"

    monkeypatch.setattr(kb_mcp, "forward", fake)
    server = kb_mcp.make_server("/data/kb")
    names = asyncio.run(_tool_names(server))
    assert names == ["kb_feedback", "kb_propose", "kb_query", "kb_show"]
    assert _call(server, "kb_query", {"hardware": "thor"}) == "RAW"
    assert _call(server, "kb_show", {"card_id": "kb-0001"}) == "RAW"
    assert seen[0] == ("/data/kb", ["query", "--json", "--hardware", "thor"])
    assert seen[1] == ("/data/kb", ["show", "kb-0001"])


async def _tool_names(server):
    tools = await server.list_tools()
    return sorted(tool.name for tool in tools)
