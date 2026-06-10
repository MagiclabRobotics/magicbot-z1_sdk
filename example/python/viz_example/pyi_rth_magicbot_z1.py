"""PyInstaller runtime hook: ensure bundled SDK shared libraries are found."""

import os
import sys


def _prepend_path(var_name: str, new_path: str) -> None:
    if not new_path:
        return
    old = os.environ.get(var_name, "")
    parts = [p for p in old.split(":") if p]
    if new_path not in parts:
        os.environ[var_name] = f"{new_path}:{old}" if old else new_path


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _prepend_path("LD_LIBRARY_PATH", sys._MEIPASS)

