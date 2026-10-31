"""arena-evidence-seal: evidence-passport seal over an arena benchmark."""

from .seal import build_manifest, seal
from .verify import verify_bundle

__all__ = ["build_manifest", "seal", "verify_bundle"]
__version__ = "0.1.0"
