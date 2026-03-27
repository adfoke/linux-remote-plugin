from __future__ import annotations

import sys
from importlib import import_module


_NEW_PACKAGE = "linux_remote_tool"
_SUBMODULES = (
    "audit",
    "cli",
    "codex_bridge",
    "config",
    "models",
    "runtime_adapter",
    "safety",
    "session_manager",
    "ssh",
    "tools",
)

_pkg = import_module(_NEW_PACKAGE)
sys.modules[__name__] = _pkg

for _submodule in _SUBMODULES:
    sys.modules[f"{__name__}.{_submodule}"] = import_module(f"{_NEW_PACKAGE}.{_submodule}")
