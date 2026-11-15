"""VoiceLens project policy checker.

  R1  No label leakage: analysis code (backend/voicelens/analyze/) must not mention ground truth
      or gold-label names. Only evaluation code may read them.
  R2  Determinism: generator code (backend/voicelens/generate/) must not use the global `random`
      module, global numpy.random functions, or the wall clock.
  R3  No secrets: no hard-coded API keys, passwords or DB URLs with passwords.
  R4  Independent analysis: analysis code may import only generate.contract / generate.config (schema, fixed
      dates) - never the generator's templates, world, taxonomy, build or edge cases, and never evaluate/.
      Lexicons are written independently, so accuracy is not "reverse-engineering the generator".

A line ending with "# policy: allow" is skipped (only with the owner's approval).

Usage:
  python scripts/policy_check.py          # scan the project, exit 1 on violations
  python scripts/policy_check.py --hook   # Claude Code PostToolUse hook (exit 2 => Claude must fix)
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "voicelens"

SCANNED_SUFFIXES = {".py", ".toml", ".yml", ".yaml", ".json", ".ini", ".cfg"}
SKIPPED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "data", "tests", ".claude",
                "prompts", "dist", "build", "frontend"}
ALLOW_MARKER = "# policy: allow"

LEAK_TERMS = re.compile(r"\b(ground_truth|issue_type|true_sentiment|true_theme|gold_label|human_label)\b")

GENERATOR_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(?:voicelens|\.\.)\.?(?:generate(?:\.(?!contract\b|config\b)\w+|\s+import\s+(?!contract\b|config\b)\w)"
    r"|evaluate\b)")

NONDET_RULES = [
    (re.compile(r"^\s*(import\s+random\b|from\s+random\s+import\b)"),
     "uses the global 'random' module; use the seeded numpy Generator passed in"),
    (re.compile(r"\b(np|numpy)\.random\.(?!default_rng\b|Generator\b|PCG64\b|SeedSequence\b)\w+"),
     "calls a global numpy.random function; use rng = np.random.default_rng(seed)"),
    (re.compile(r"\b(datetime\.now|datetime\.utcnow|date\.today|time\.time)\s*\("),
     "reads the wall clock; derive dates from a fixed reference date"),
]

SECRET_RULES = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "looks like an API key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "looks like a GitHub token"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
     "hard-coded credential; read it from an environment variable"),
    (re.compile(r"postgres(?:ql)?(?:\+\w+)?://[^:\s/@]+:[^@\s]+@"),
     "database URL with an embedded password; read it from an environment variable"),
]


@dataclass(frozen=True)
class Violation:
    rule: str
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.path}:{self.line}: {self.message}"


def _in_area(rel_parts: tuple[str, ...], area: str) -> bool:
    dirs = rel_parts[:-1]
    return PACKAGE in dirs and area in dirs[dirs.index(PACKAGE):]


def check_file(path: Path, root: Path = ROOT) -> list[Violation]:
    path = Path(path).resolve()
    root = Path(root).resolve()
    try:
        rel = path.relative_to(root)
    except ValueError:
        return []
    if path.suffix.lower() not in SCANNED_SUFFIXES or any(p in SKIPPED_DIRS for p in rel.parts[:-1]):
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    rel_str = rel.as_posix()
    is_analyze = _in_area(rel.parts, "analyze")
    is_generate = _in_area(rel.parts, "generate")
    found: list[Violation] = []

    for n, line in enumerate(lines, start=1):
        if line.rstrip().endswith(ALLOW_MARKER):
            continue
        if is_analyze and path.suffix == ".py":
            m = LEAK_TERMS.search(line)
            if m:
                found.append(Violation("R1-leakage", rel_str, n,
                                       f"analysis code mentions '{m.group(1)}'; analysis must never use ground truth"))
            if GENERATOR_IMPORT.search(line):
                found.append(Violation("R4-independence", rel_str, n,
                                       "analysis imports generator internals or evaluate/; only generate.contract/config allowed"))
        if is_generate and path.suffix == ".py":
            for pattern, msg in NONDET_RULES:
                if pattern.search(line):
                    found.append(Violation("R2-determinism", rel_str, n, msg))
        for pattern, msg in SECRET_RULES:
            if pattern.search(line):
                found.append(Violation("R3-secret", rel_str, n, msg))
    return found


def check_repo(root: Path = ROOT) -> list[Violation]:
    root = Path(root).resolve()
    found: list[Violation] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            found.extend(check_file(path, root))
    return found


def _run_hook() -> int:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
        file_path = (data.get("tool_input") or {}).get("file_path")
        if not file_path:
            return 0
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ROOT)
        violations = check_file(Path(file_path), root)
    except Exception:
        return 0
    if not violations:
        return 0
    print("Project policy violation(s) - fix before continuing:", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    print("See CLAUDE.md section 2 (hard rules).", file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    if "--hook" in argv:
        return _run_hook()
    violations = check_repo(ROOT)
    if violations:
        print(f"{len(violations)} policy violation(s):")
        for v in violations:
            print(f"  {v}")
        return 1
    print("Policy check passed: no leakage, determinism or secret violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
