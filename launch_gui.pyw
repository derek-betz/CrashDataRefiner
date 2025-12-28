import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "crash_data_refiner"

if SRC.exists():
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from crash_data_refiner.gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
