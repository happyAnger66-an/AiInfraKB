"""MCP 入口：把工具参数转成 kb 命令行，不解析知识库内容。"""

from __future__ import annotations

import os
import subprocess

from mcp.server.fastmcp import FastMCP


class KbMcpError(Exception):
    def __init__(self, returncode: int, message: str):
        self.returncode = returncode
        super().__init__(message)


def command(root: str | None, args: list[str]) -> list[str]:
    if root:
        return ["kb", "--root", root, *args]
    return ["kb", *args]


def _option(flag: str, value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if item:
                parts.extend([flag, item])
        return parts
    return [flag, value]


def query_args(hardware=None, model=None, technique=None, text=None) -> list[str]:
    args = ["query", "--json"]
    args += _option("--hardware", hardware)
    args += _option("--model", model)
    args += _option("--technique", technique)
    args += _option("--text", text)
    return args


def propose_args(
    *,
    type: str,
    title: str,
    claim: str,
    hardware=None,
    model=None,
    technique=None,
    evidence_ref=None,
    author: str,
    today: str | None = None,
) -> list[str]:
    args = ["propose", "--type", type, "--title", title, "--claim", claim]
    args += _option("--hardware", hardware)
    args += _option("--model", model)
    args += _option("--technique", technique)
    args += _option("--evidence-ref", evidence_ref)
    args += ["--author", author]
    args += _option("--today", today)
    return args


def feedback_args(card_id: str, *, result: str, env: str, author: str, note: str = "", at: str | None = None) -> list[str]:
    flag = "--worked" if result == "worked" else "--failed"
    args = ["feedback", card_id, flag, "--env", env, "--author", author]
    args += _option("--note", note)
    args += _option("--at", at)
    return args


def forward(root: str | None, args: list[str], run=subprocess.run) -> str:
    proc = run(command(root, args), capture_output=True, text=True)
    if proc.returncode != 0:
        message = proc.stderr if proc.stderr else proc.stdout
        raise KbMcpError(proc.returncode, message)
    return proc.stdout


def make_server(root: str | None) -> FastMCP:
    server = FastMCP("kb")

    @server.tool()
    def kb_query(hardware: str | None = None, model: str | None = None, technique: str | None = None, text: str | None = None) -> str:
        """按硬件、模型、技巧或文本查询知识卡。返回 kb query --json 的原始输出。"""
        return forward(root, query_args(hardware=hardware, model=model, technique=technique, text=text))

    @server.tool()
    def kb_show(card_id: str) -> str:
        """打印一张知识卡的原文。"""
        return forward(root, ["show", card_id])

    @server.tool()
    def kb_propose(
        type: str,
        title: str,
        claim: str,
        author: str,
        hardware: list[str] | None = None,
        model: list[str] | None = None,
        technique: list[str] | None = None,
        evidence_ref: list[str] | None = None,
        today: str | None = None,
    ) -> str:
        """把一条候选知识写入 inbox。"""
        return forward(
            root,
            propose_args(
                type=type,
                title=title,
                claim=claim,
                hardware=hardware,
                model=model,
                technique=technique,
                evidence_ref=evidence_ref,
                author=author,
                today=today,
            ),
        )

    @server.tool()
    def kb_feedback(
        card_id: str,
        result: str,
        env: str,
        author: str,
        note: str = "",
        at: str | None = None,
    ) -> str:
        """记录一张知识卡这次是否有效。result 取 worked 或 failed。"""
        return forward(
            root,
            feedback_args(card_id, result=result, env=env, author=author, note=note, at=at),
        )

    return server


def main() -> None:
    root = os.environ.get("AIINFRAKB_ROOT") or None
    make_server(root).run()


if __name__ == "__main__":
    main()
