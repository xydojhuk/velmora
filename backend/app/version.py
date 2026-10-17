"""Single source of truth for the app version: repository root VERSION."""
from pathlib import Path
import re


def get_version() -> str:
    current = Path(__file__).resolve()
    for candidate in (current.parents[1] / "VERSION", current.parents[2] / "VERSION"):
        if candidate.is_file():
            version = candidate.read_text(encoding="utf-8").strip()
            if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
                return version
            raise RuntimeError("Invalid root VERSION format")
    raise RuntimeError("Velmora VERSION file is absent from this installation")
