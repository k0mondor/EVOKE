from __future__ import annotations

import contextlib
import importlib
import io
import warnings
from types import ModuleType

_TORCH_MODULE: ModuleType | None = None


def import_torch(*, quiet: bool = True) -> ModuleType:
    """Import torch while suppressing known NumPy ABI warnings on legacy setups.

    This is a UI/runtime quality-of-life shim only. If torch truly fails to import,
    the original exception is still raised.
    """

    global _TORCH_MODULE
    if _TORCH_MODULE is not None:
        return _TORCH_MODULE

    stderr_buffer = io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stderr_context = contextlib.redirect_stderr(stderr_buffer) if quiet else contextlib.nullcontext()
        with stderr_context:
            module = importlib.import_module("torch")

    _TORCH_MODULE = module
    return module
