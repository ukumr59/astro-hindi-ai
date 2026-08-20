"""Brand-consistency and glyph-regression guard for production rendering."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREMIUM = (ROOT / "video_engine" / "premium_entry.py").read_text(encoding="utf-8")
V18 = (ROOT / "video_engine" / "premium_entry_v18.py").read_text(encoding="utf-8")
LOGO = ROOT / "assets" / "brand" / "astropratidin_logo.webp"

assert LOGO.exists(), f"Missing master brand asset: {LOGO}"
assert "astropratidin_logo.webp" in PREMIUM
assert "ImageOps.contain" in PREMIUM
assert "base.outro = premium_outro" in PREMIUM
assert "d.ellipse" not in PREMIUM
assert "ॐ" not in PREMIUM
assert "✦" not in PREMIUM
assert "•" not in PREMIUM

# V18 must use the image logo for the English brand name. The bundled
# Devanagari production font does not contain Latin glyphs, so drawing
# AstroPratidin as text creates tofu/square boxes.
assert "v17._brand_logo(canvas, 402, 250, 276)" in V18
assert "base.outro = premium_outro" in V18
assert "base.fit(draw, BRAND" not in V18
assert 'draw.text(((base.W - (b[2] - b[0])) / 2, 1170)' not in V18
print("Brand + glyph consistency guard: PASS")
