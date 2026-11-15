"""SHA-256 manifest of the committed decision pack.

One definition is shared by the pipeline and ``scripts/build_manifest.py`` so that
``make demo`` and ``make verify`` write the same manifest.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

MANIFEST_NAME = "MANIFEST.sha256"
MANIFEST_PATTERNS = (
    "data/demo/*.csv",
    "artifacts/results/*.csv",
    "artifacts/results/*.json",
    "artifacts/figures/*.png",
    "artifacts/*.sqlite",
    "excel/*.xlsx",
    "presentation/*.pptx",
    "report/*.pdf",
)
# Large outputs that are regenerated locally and not committed (see .gitignore).
MANIFEST_EXCLUDED = ("data/demo/transactions.csv", "artifacts/results/graph_edges.csv")


def manifest_paths(root: Path) -> list[Path]:
    root = Path(root)
    excluded = {root / relative for relative in MANIFEST_EXCLUDED}
    paths = {path for pattern in MANIFEST_PATTERNS for path in root.glob(pattern)}
    return sorted(path for path in paths if path not in excluded)


def write_manifest(root: Path) -> int:
    """Write MANIFEST.sha256 for every manifest path present and return the entry count."""
    root = Path(root)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
        for path in manifest_paths(root)
    ]
    (root / MANIFEST_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)
