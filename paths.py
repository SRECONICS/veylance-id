import os
import sys


def is_frozen():
    """True once this is running as a PyInstaller-built .exe, False when
    running from source with `python main.py`."""
    return getattr(sys, "frozen", False)


def app_root():
    """Directory holding bundled, read-only resources (currently just
    models/). In a frozen build this is PyInstaller's extraction dir
    (sys._MEIPASS) — fresh each launch, fine for read-only assets. In
    dev mode it's the project root, same as always."""

    if is_frozen():
        return sys._MEIPASS

    return os.path.dirname(os.path.abspath(__file__))


def data_root():
    """Directory for writable, persistent app data — the database,
    enrolled face samples, intruder snapshots. Must NOT be inside the
    frozen app's temp extraction dir, since that's wiped after every run.

    In dev mode this is the project's data/ folder, exactly like before
    every checkpoint up to now — nothing changes for `python main.py`.
    In a frozen build it's %LOCALAPPDATA%\\VeylanceID, the standard place
    a Windows desktop app keeps its per-user data."""

    if is_frozen():
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "VeylanceID")
    else:
        path = os.path.join(app_root(), "data")

    os.makedirs(path, exist_ok=True)
    return path
