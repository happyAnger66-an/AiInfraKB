import copy
import shutil
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

BODY = """
## 结论

示例结论。

## 适用条件

示例条件。

## 证据

示例证据。
"""

BASE_META = {
    "id": "kb-0001",
    "type": "lesson",
    "title": "示例：某算子在 FP8 下保持 FP16",
    "status": "active",
    "claim": "示例：误差升高 4 倍；保持 FP16 后回到基线，延迟多 3%",
    "applies_to": {
        "hardware": ["thor"],
        "software": {"tensorrt": ">=10.8,<11"},
        "models": ["pi05"],
        "techniques": ["fp8-quant"],
        "precision": ["fp8"],
    },
    "evidence": [
        {
            "kind": "benchmark",
            "ref": "evidence/kb-0001/run.md",
            "env": {"gpu": "thor"},
            "result": {"latency_ms": 11.2},
        }
    ],
    "confidence": "measured",
    "authors": ["agent:test"],
    "created": "2026-10-01",
    "last_verified": "2026-10-10",
    "review_by": "2027-04-10",
    "visibility": "public",
}

TYPE_DIRS = {
    "fact": "facts",
    "lesson": "lessons",
    "technique": "techniques",
    "benchmark": "benchmarks",
    "decision": "decisions",
}


def make_meta(**overrides):
    meta = copy.deepcopy(BASE_META)
    for key, value in overrides.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value
    return meta


def dump_card(meta, body=BODY):
    # 日期写成不加引号的 YAML 日期，覆盖 PyYAML 把它解析成 date 对象的路径。
    text = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
    for key in ("created", "last_verified", "review_by"):
        if key in meta:
            text = text.replace(f"{key}: '{meta[key]}'", f"{key}: {meta[key]}")
    return f"---\n{text}---\n{body}"


class KbFixture:
    def __init__(self, root: Path):
        self.root = root

    def add_card(self, meta=None, body=BODY, rel_path=None, with_evidence=True):
        meta = meta if meta is not None else make_meta()
        if rel_path is None:
            rel_path = f"cards/{TYPE_DIRS[meta['type']]}/{meta['id']}.md"
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_card(meta, body), encoding="utf-8")
        if with_evidence:
            for ev in meta.get("evidence", []):
                ref = ev["ref"]
                if not ref.startswith(("http://", "https://")):
                    ev_path = self.root / ref
                    ev_path.parent.mkdir(parents=True, exist_ok=True)
                    ev_path.write_text("raw data\n", encoding="utf-8")
        return path


@pytest.fixture
def kb_root(tmp_path):
    root = tmp_path / "kb"
    root.mkdir()
    shutil.copy(REPO_ROOT / "kb.toml", root / "kb.toml")
    shutil.copytree(REPO_ROOT / "schema", root / "schema")
    shutil.copytree(REPO_ROOT / "vocab", root / "vocab")
    for sub in TYPE_DIRS.values():
        (root / "cards" / sub).mkdir(parents=True)
    (root / "archive").mkdir()
    (root / "evidence").mkdir()
    return KbFixture(root)
