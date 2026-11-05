import json
import subprocess

import pytest
from configuration_auditor.core import DEFAULT_RULES, audit, write_reports


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


@pytest.fixture
def sample(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_text("Readme")
    (root / "CHANGELOG.md").write_text("History")
    (root / "pyproject.toml").write_text('[project]\nversion="1.0.0"\n')
    folder = root / ".github" / "workflows"
    folder.mkdir(parents=True)
    (folder / "ci.yml").write_text("name: CI\n")
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-m", "Initial fixture")
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps(DEFAULT_RULES | {"min_commits": 1}))
    return root, rules


def test_compliant(sample):
    assert audit(*sample)["passed"]


@pytest.mark.parametrize("name", ["README.md", "CHANGELOG.md", "pyproject.toml"])
def test_missing_file(sample, name):
    root, rules = sample
    (root / name).unlink()
    assert not audit(root, rules)["passed"]


@pytest.mark.parametrize(
    "text",
    [
        '[project]\nversion="01.0.0"',
        "[project]\nversion=1",
        "broken{",
        '[tool.sample]\nname="missing"',
    ],
)
def test_invalid_version(sample, text):
    root, rules = sample
    (root / "pyproject.toml").write_text(text)
    assert any(f["rule"] == "version" and not f["passed"] for f in audit(root, rules)["findings"])


def test_missing_git(sample, tmp_path):
    root, rules = sample
    # Audit a separate folder so Git cannot fall back to a parent repository.
    empty = tmp_path / "empty"
    empty.mkdir()
    assert any(f["rule"] == "git" and not f["passed"] for f in audit(empty, rules)["findings"])


def test_min_commits(sample):
    root, rules = sample
    rules.write_text(json.dumps(DEFAULT_RULES))
    assert any(f["rule"] == "commits" and not f["passed"] for f in audit(root, rules)["findings"])


def test_missing_ci(sample):
    root, rules = sample
    (root / ".github" / "workflows" / "ci.yml").unlink()
    assert any(f["rule"] == "ci" and not f["passed"] for f in audit(root, rules)["findings"])


@pytest.mark.parametrize(
    "value",
    [
        "{",
        "[]",
        '{"min_commits":-1}',
        '{"severity":[]}',
        '{"required_files":["../secret"]}',
        '{"unknown":true}',
    ],
)
def test_corrupt_rules(sample, value):
    root, rules = sample
    rules.write_text(value)
    result = audit(root, rules)
    assert not result["passed"] and result["findings"][0]["rule"] == "config"


def test_html_escape(tmp_path):
    result = {
        "passed": False,
        "findings": [
            dict(rule="files", severity="error", passed=False, message="<script>bad</script>")
        ],
    }
    write_reports(result, tmp_path / "report.json", tmp_path / "report.html")
    assert "&lt;script&gt;" in (tmp_path / "report.html").read_text()
    assert json.loads((tmp_path / "report.json").read_text()) == result
