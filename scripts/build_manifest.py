from __future__ import annotations

import hashlib
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    patterns = (
        "data/demo/*.csv",
        "artifacts/results/*.csv",
        "artifacts/results/*.json",
        "artifacts/figures/*.png",
        "artifacts/*.sqlite",
        "excel/*.xlsx",
        "presentation/*.pptx",
        "report/*.pdf",
    )
    paths = sorted({path for pattern in patterns for path in root.glob(pattern)})
    excluded = {
        root / "data" / "demo" / "transactions.csv",
        root / "artifacts" / "results" / "graph_edges.csv",
    }
    paths = [path for path in paths if path not in excluded]
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
        for path in paths
    ]
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} SHA-256 entries.")


if __name__ == "__main__":
    main()
