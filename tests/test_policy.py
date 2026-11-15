"""Tests for scripts/policy_check.py: labels separate from model input, generator determinism, no secrets."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("policy_check", ROOT / "scripts" / "policy_check.py")
policy_check = importlib.util.module_from_spec(_spec)
sys.modules["policy_check"] = policy_check
_spec.loader.exec_module(policy_check)

PKG = "backend/voicelens"


def _write(root: Path, rel: str, code: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    return path


def _rules(violations):
    return {v.rule for v in violations}


def test_real_project_has_no_violations():
    violations = policy_check.check_repo(ROOT)
    assert violations == [], "\n".join(str(v) for v in violations)


def test_analysis_reading_ground_truth_is_caught(tmp_path):
    f = _write(tmp_path, f"{PKG}/analyze/sentiment.py", "gt = pd.read_csv('data/ground_truth.csv')\n")
    assert "R1-leakage" in _rules(policy_check.check_file(f, tmp_path))


def test_analysis_using_gold_label_column_is_caught(tmp_path):
    f = _write(tmp_path, f"{PKG}/analyze/themes.py", "x = df['true_sentiment']\n")
    assert "R1-leakage" in _rules(policy_check.check_file(f, tmp_path))


def test_evaluation_may_read_ground_truth(tmp_path):
    f = _write(tmp_path, f"{PKG}/evaluate/metrics.py", "gt = pd.read_csv('data/ground_truth.csv')\n")
    assert policy_check.check_file(f, tmp_path) == []


def test_generator_nondeterminism_is_caught(tmp_path):
    for code in ("import random\n", "from random import choice\n", "x = np.random.randint(0, 5)\n",
                 "today = date.today()\n"):
        f = _write(tmp_path, f"{PKG}/generate/text.py", code)
        assert "R2-determinism" in _rules(policy_check.check_file(f, tmp_path)), code


def test_generator_seeded_rng_is_allowed(tmp_path):
    f = _write(tmp_path, f"{PKG}/generate/text.py", "rng = np.random.default_rng(seed)\nn = rng.integers(0, 5)\n")
    assert policy_check.check_file(f, tmp_path) == []


def test_hard_coded_db_password_is_caught(tmp_path):
    url = "postgresql://postgres:" + "pw123456" + "@localhost:5432/voicelens"
    f = _write(tmp_path, f"{PKG}/db/session.py", f"URL = '{url}'\n")
    assert "R3-secret" in _rules(policy_check.check_file(f, tmp_path))


def test_allow_marker_skips_line(tmp_path):
    f = _write(tmp_path, f"{PKG}/analyze/doc.py", "# never read ground_truth here  # policy: allow\n")
    assert policy_check.check_file(f, tmp_path) == []



def test_analysis_importing_generator_internals_is_caught(tmp_path):
    for code in ("from ..generate.templates import EN_FRAMES\n", "from voicelens.generate import world\n",
                 "from ..generate.taxonomy import THEMES\n", "from ..evaluate.metrics import f1\n"):
        f = _write(tmp_path, f"{PKG}/analyze/sentiment.py", code)
        assert "R4-independence" in _rules(policy_check.check_file(f, tmp_path)), code


def test_analysis_may_import_contract_and_config(tmp_path):
    code = "from ..generate.contract import SENT\nfrom ..generate import config\nfrom ..db.engine import get_engine\n"
    f = _write(tmp_path, f"{PKG}/analyze/sentiment.py", code)
    assert policy_check.check_file(f, tmp_path) == []
