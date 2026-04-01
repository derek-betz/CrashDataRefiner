from __future__ import annotations

import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_2101166_official_boundary_fixture_matches_reference_folder() -> None:
    official = REPO_ROOT / "raw-crash-data-for-reference" / "2101166" / "2101166_Relevance Boundary.kmz"
    test_fixture = REPO_ROOT / "tests" / "refiner_inputs" / "2101166_Relevance Boundary.kmz"

    assert official.exists(), f"Missing official reference boundary: {official}"
    assert test_fixture.exists(), f"Missing test fixture boundary: {test_fixture}"
    assert _sha256(test_fixture) == _sha256(official)
