"""OpenClaw host-discovery contract in the converter spec."""

import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")


def _extract_probe_script():
    start = SKILL.index('SCRIPT_PATH=""')
    end = SKILL.index('\nif [ -z "$SCRIPT_PATH" ]', start)
    return SKILL[start:end] + '\nprintf "%s" "$SCRIPT_PATH"\n'


def _probe_env(home, state_dir=None):
    env = os.environ.copy()
    env.update({"HOME": str(home)})
    if state_dir is None:
        env.pop("OPENCLAW_STATE_DIR", None)
    else:
        env["OPENCLAW_STATE_DIR"] = str(state_dir)
    env.pop("HERMES_AGENT", None)
    env.pop("HERMES_HOME", None)
    return env


@pytest.mark.parametrize(
    "layout",
    [
        "personal-flat",
        "personal-grouped",
        "personal-deep",
        "personal-custom-state",
        "workspace-flat",
        "workspace-grouped",
        "workspace-deep",
    ],
)
@pytest.mark.skipif(
    os.name == "nt",
    reason="the probe uses POSIX Bash path semantics; the same cases run in Ubuntu CI",
)
def test_openclaw_extractor_probe_discovers_supported_layouts(tmp_path, layout):
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    nested = project / "src" / "nested"
    nested.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)

    roots = {
        "personal-flat": home / ".openclaw" / "skills" / "book-to-skill",
        "personal-grouped": home / ".openclaw" / "skills" / "group" / "subgroup" / "book-to-skill",
        "personal-deep": home / ".openclaw" / "skills" / "one" / "two" / "three" / "four" / "five" / "six" / "book-to-skill",
        "personal-custom-state": tmp_path / "custom-openclaw-state" / "skills" / "book-to-skill",
        "workspace-flat": project / "skills" / "book-to-skill",
        "workspace-grouped": project / "skills" / "group" / "subgroup" / "book-to-skill",
        "workspace-deep": project / "skills" / "one" / "two" / "three" / "four" / "five" / "six" / "book-to-skill",
    }
    extractor = roots[layout] / "scripts" / "extract.py"
    extractor.parent.mkdir(parents=True)
    extractor.touch()

    state_dir = roots[layout].parents[1] if layout == "personal-custom-state" else None
    result = subprocess.run(
        ["bash", "-c", _extract_probe_script()],
        cwd=nested,
        env=_probe_env(home, state_dir=state_dir),
        check=True,
        capture_output=True,
        text=True,
    )
    selected = Path(result.stdout.strip())
    if not selected.is_absolute():
        selected = nested / selected
    assert selected.resolve() == extractor.resolve()


def test_openclaw_host_layouts_are_documented():
    assert "${OPENCLAW_STATE_DIR:-~/.openclaw}/skills" in SKILL
    assert "skills/book-to-skill/scripts/extract.py" in SKILL
    assert "openclaw skills list" in SKILL
    assert "OPENCLAW_STATE_DIR" in SKILL
    assert "~/.agents/skills` only with default state" in SKILL
