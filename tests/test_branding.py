"""Brand-consistency regression guard for the production renderer."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREMIUM = (ROOT / "video_engine" / "premium_entry.py").read_text(encoding="utf-8")
LOGO = ROOT / "assets" / "brand" / "astropratidin_logo.webp"

assert LOGO.exists(), f"Missing master brand asset: {LOGO}"
assert "astropratidin_logo.webp" in PREMIUM
assert "ImageOps.contain" in PREMIUM
assert "base.outro = premium_outro" in PREMIUM
assert "d.ellipse" not in PREMIUM
assert "ॐ" not in PREMIUM
assert "✦" not in PREMIUM
assert "•" not in PREMIUM
print("Brand consistency guard: PASS")
