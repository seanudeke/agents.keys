"""Compatibility entry point: python mine.py --output runs/census-YYYYMMDD."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from awkeys.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["mine", *sys.argv[1:]]))
