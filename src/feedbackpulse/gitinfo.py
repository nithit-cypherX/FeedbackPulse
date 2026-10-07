"""Git facts that recorded results depend on.

Shared because both the evaluation result and the registry entry claim "this
came from that commit", and the two must answer the question the same way.
"""

import subprocess

# Everything this project writes as a result rather than reads as an input.
# Changes here must not mark a run dirty: the question the flag answers is
# whether the code and configuration behind the numbers were committed, and a
# previous result file sitting uncommitted says nothing about that.
OUTPUT_PREFIXES = ("reports/",)

# Files that decide what a prediction is. If any of them moved between the
# commit an evaluation ran at and the commit being registered, that evaluation
# no longer describes the code being released.
BEHAVIOUR_PATHS = (
    "src/feedbackpulse/inference.py",
    "src/feedbackpulse/model_files.py",
    "src/feedbackpulse/dataset.py",
    "src/feedbackpulse/evaluation.py",
    "src/feedbackpulse/evaluate.py",
    "pyproject.toml",
    "uv.lock",
)


class GitUnavailable(RuntimeError):
    """Git could not answer, so no claim about provenance can be made."""


def _git(*args: str, strip: bool = True) -> str:
    """Run a git command.

    `strip` must be False for porcelain output: a status line for a
    worktree-only change starts with a space, and stripping it shifts every
    column left so the parsed path loses its first character.
    """
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitUnavailable(f"git {' '.join(args)} failed") from exc
    return out.strip() if strip else out.rstrip("\n")


def uncommitted_inputs(porcelain_status: str) -> list[str]:
    """Paths from `git status --porcelain` that count as uncommitted inputs."""
    paths = []
    for line in porcelain_status.splitlines():
        if not line.strip():
            continue
        # Porcelain v1: two status characters, a space, then the path. A rename
        # reads "old -> new", and either side changing is a real change.
        candidates = [part.strip().strip('"') for part in line[3:].split(" -> ")]
        if any(not path.startswith(OUTPUT_PREFIXES) for path in candidates if path):
            paths.append(line[3:])
    return paths


def code_version() -> dict:
    """Commit, and whether the inputs behind the current state were committed."""
    try:
        commit = _git("rev-parse", "HEAD")
        status = _git("status", "--porcelain", strip=False)
    except GitUnavailable:
        return {"commit": None, "dirty": None, "uncommitted": None}
    dirty = uncommitted_inputs(status)
    return {"commit": commit, "dirty": bool(dirty), "uncommitted": dirty}


def behaviour_changed_between(commit: str, other: str = "HEAD") -> list[str]:
    """Behaviour-deciding files that differ between two commits."""
    changed = _git("diff", "--name-only", commit, other, "--", *BEHAVIOUR_PATHS)
    return [line for line in changed.splitlines() if line.strip()]
