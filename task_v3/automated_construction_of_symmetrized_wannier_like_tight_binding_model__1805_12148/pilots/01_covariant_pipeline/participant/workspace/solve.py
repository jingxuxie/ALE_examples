"""Entrypoint; also works when copied alone into the initial attempt directory."""

from pathlib import Path
import sys

workspace = Path(__file__).resolve().parents[1] / "participant/workspace"
if workspace.is_dir():
    sys.path.append(str(workspace))

from pipeline import main


if __name__ == "__main__":
    main()
