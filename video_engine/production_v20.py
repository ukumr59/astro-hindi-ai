"""V20 production entry point.

Uses the user's supplied AstroPratidin master logo PNG. The existing premium
renderer remains responsible for scene composition; this wrapper makes the
approved master asset explicit and prevents fallback to any generated logo.
"""
from pathlib import Path

from . import premium_entry as premium

ROOT = Path(__file__).resolve().parents[1]
APPROVED_LOGO = ROOT / "assets" / "brand" / "astropratidin_logo_256.png"

if not APPROVED_LOGO.exists():
    raise RuntimeError(f"Approved AstroPratidin master logo missing: {APPROVED_LOGO}")

premium.BRAND_LOGO = APPROVED_LOGO
premium.main()
