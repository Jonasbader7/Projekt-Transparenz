"""Einheitliches Logging für CLI, App und Update-Pipeline."""

from __future__ import annotations

import logging

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if getattr(root, "_transparenz_configured", False):
        root.setLevel(level)
        return
    logging.basicConfig(level=level, format=_FORMAT)
    root._transparenz_configured = True  # type: ignore[attr-defined]
