"""Reproducibility: generate twice with the same seed + scale into temp dirs and compare every file's SHA-256 from
the manifests; also compare against the manifest of the data being validated (proves it is the seeded output)."""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from ..generate.__main__ import generate


def _sums(manifest: dict) -> dict[str, str]:
    return {f["path"]: f["sha256"] for f in manifest["files"]}


def reproducibility(seed: int, scale: float, reference_manifest: Path | None = None) -> dict:
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="voicelens_repro_") as tmp:
        m1 = generate(scale, seed, Path(tmp) / "run1")[2]
        m2 = generate(scale, seed, Path(tmp) / "run2")[2]
    a, b = _sums(m1), _sums(m2)
    diff = sorted(p for p in a.keys() | b.keys() if a.get(p) != b.get(p))
    result = {"seed": seed, "scale": scale, "files_compared": len(a), "runs_identical": not diff,
              "differing_files": diff, "seconds": round(time.perf_counter() - t0, 1)}
    if reference_manifest and reference_manifest.exists():
        ref = json.loads(reference_manifest.read_text(encoding="utf-8"))
        if ref.get("seed") == seed and ref.get("scale") == scale:
            d = sorted(p for p in a if _sums(ref).get(p) != a[p])
            result["matches_validated_data"] = not d
            result["differing_from_validated_data"] = d
    result["passed"] = result["runs_identical"] and result.get("matches_validated_data", True)
    return result
