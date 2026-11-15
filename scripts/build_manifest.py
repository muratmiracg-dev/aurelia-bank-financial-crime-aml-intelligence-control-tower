from __future__ import annotations

from pathlib import Path

from aurelia_aml.manifest import write_manifest


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    print(f"Wrote {write_manifest(root)} SHA-256 entries.")


if __name__ == "__main__":
    main()
