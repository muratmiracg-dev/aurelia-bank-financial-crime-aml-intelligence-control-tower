from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    targets = [
        *sorted((root / "data" / "demo").glob("*.csv")),
        *sorted((root / "artifacts" / "results").glob("*.csv")),
        *sorted((root / "artifacts" / "results").glob("*.json")),
        *sorted((root / "artifacts" / "figures").glob("*.png")),
        root / "artifacts" / "aurelia_aml_demo.sqlite",
        root / "MANIFEST.sha256",
    ]
    for path in targets:
        if path.exists() and path.is_file():
            path.unlink()
    print(f"Removed {sum(not path.exists() for path in targets)} generated files.")


if __name__ == "__main__":
    main()
