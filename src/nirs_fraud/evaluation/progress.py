from __future__ import annotations

import sys


def render_progress(prefix: str, completed: int, total: int) -> None:
    total = max(total, 1)
    width = 28
    ratio = completed / total
    filled = min(width, int(ratio * width))
    bar = "#" * filled + "-" * (width - filled)
    sys.stderr.write(f"\r[{prefix}] [{bar}] {completed}/{total}")
    sys.stderr.flush()


def finish_progress() -> None:
    sys.stderr.write("\n")
    sys.stderr.flush()
