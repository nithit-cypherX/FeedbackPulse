"""The dirty-tree flag must describe inputs, not outputs.

The flag ends up in the recorded evaluation result as the claim "this run can be
reproduced from this commit". A result file left uncommitted from an earlier run
does not change the code, so it must not raise the flag — otherwise every repeat
run in T08 would look unreproducible.
"""

from feedbackpulse import gitinfo
from feedbackpulse.gitinfo import uncommitted_inputs


def test_clean_tree_has_no_uncommitted_inputs():
    assert uncommitted_inputs("") == []


def test_changed_source_counts():
    assert uncommitted_inputs(" M src/feedbackpulse/inference.py") == [
        "src/feedbackpulse/inference.py"
    ]


def test_untracked_config_counts():
    assert uncommitted_inputs("?? pyproject.toml") == ["pyproject.toml"]


def test_result_and_report_files_do_not_count():
    status = " M reports/P02-T05-evaluation-result.json\n?? reports/P02-evidence.md"
    assert uncommitted_inputs(status) == []


def test_mixed_status_reports_only_the_input():
    status = (
        " M reports/P02-T05-evaluation-result.json\n M src/feedbackpulse/evaluate.py"
    )
    assert uncommitted_inputs(status) == ["src/feedbackpulse/evaluate.py"]


def test_rename_into_outputs_from_an_input_still_counts():
    assert uncommitted_inputs("R  src/old.py -> reports/old.py") == [
        "src/old.py -> reports/old.py"
    ]


def test_rename_inside_outputs_does_not_count():
    assert uncommitted_inputs("R  reports/a.md -> reports/b.md") == []


def test_status_is_read_without_stripping_the_leading_column(monkeypatch):
    """A worktree-only change starts its status line with a space.

    Stripping the command output shifts every column left, and the parsed path
    then loses its first character. Reported paths end up in the recorded
    evaluation result, so a mangled one would misname what was uncommitted.
    """
    captured = {}

    def fake_git(*args, strip=True):
        if args[0] == "status":
            captured["strip"] = strip
            return " M src/feedbackpulse/inference.py"
        return "0" * 40

    monkeypatch.setattr(gitinfo, "_git", fake_git)
    result = gitinfo.code_version()
    assert captured["strip"] is False
    assert result["uncommitted"] == ["src/feedbackpulse/inference.py"]
    assert result["dirty"] is True
