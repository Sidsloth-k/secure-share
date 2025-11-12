"""Auth package bridge for legacy auth.py module."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent.parent
_LEGACY_PATH = _ROOT / "auth.py"

if not _LEGACY_PATH.exists():
    raise ImportError(f"Legacy auth module not found at {_LEGACY_PATH}")

_SPEC = spec_from_file_location("auth_legacy", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load legacy auth module from {_LEGACY_PATH}")

_MODULE = module_from_spec(_SPEC)
sys.modules.setdefault("auth_legacy", _MODULE)
_SPEC.loader.exec_module(_MODULE)  # type: ignore[assignment]

Auth = _MODULE.Auth  # type: ignore[attr-defined]

__all__ = ["Auth"]


