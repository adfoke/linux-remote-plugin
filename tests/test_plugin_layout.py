import json
import runpy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_alma_wrapper_loads_from_repo_checkout():
    payload = runpy.run_path(str(REPO_ROOT / ".alma-plugin" / "runtime_adapter.py"))

    assert "get_tools" in payload
    assert "invoke" in payload


def test_alma_manifest_points_to_local_wrapper():
    manifest = json.loads((REPO_ROOT / ".alma-plugin" / "manifest.json").read_text())

    assert manifest["main"] == "./runtime_adapter.py"


def test_codex_manifest_exposes_skills():
    manifest = json.loads((REPO_ROOT / ".codex-plugin" / "plugin.json").read_text())

    assert manifest["skills"] == "./skills/"


def test_codex_skill_entry_exists():
    assert (REPO_ROOT / "skills" / "lr" / "SKILL.md").exists()
