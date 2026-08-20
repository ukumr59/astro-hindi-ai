"""Brand, layout, and glyph-regression guard for production rendering."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREMIUM = (ROOT / "video_engine" / "premium_entry.py").read_text(encoding="utf-8")
LOGO = ROOT / "assets" / "brand" / "astropratidin_logo.webp"

assert LOGO.exists(), f"Missing master brand asset: {LOGO}"
assert "astropratidin_logo.webp" in PREMIUM
assert "ImageOps.contain" in PREMIUM
assert "_brand_header(canvas, draw)" in PREMIUM
assert "HEADER_LOGO_SIZE = 190" in PREMIUM
assert "HERO_TOP = 264" in PREMIUM
assert "base.outro = premium_outro" in PREMIUM

# Never redraw/retype the English brand name; the master image is the brand mark.
assert 'BRAND = "AstroPratidin"' not in PREMIUM
assert "base.fit(draw, BRAND" not in PREMIUM

# Never use decorative Unicode glyphs that can become missing-glyph boxes.
for glyph in ["ॐ", "✦", "•", "॥", "❤", "★"]:
    assert glyph not in PREMIUM, f"Unsafe decorative glyph present: {glyph}"

# Branding must not be placed directly on top of the deity hero.
assert "_logo(canvas)" in PREMIUM
assert "_brand_header(canvas, draw)" in PREMIUM
assert "_hero(canvas, image_path)" in PREMIUM

print("V19 brand/layout/glyph consistency guard: PASS")
