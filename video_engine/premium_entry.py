"""AstroPratidin premium production renderer.

Hard production rules:
- The ONLY AstroPratidin brand mark is the exact supplied file:
  assets/AstroPratidin Logo.png
- Never redraw, retype, approximate, or substitute the logo.
- Never render legacy branding or replacement footers.
- Never render English brand text with the Devanagari font.
- Audio timing remains owned by render_sync.py.
"""
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageOps
from . import render_sync as base

ROOT = Path(__file__).resolve().parents[1]
MASTER_LOGO = ROOT / "assets" / "AstroPratidin Logo.png"
GOLD = (247, 202, 77, 255)
GOLD_SOFT = (255, 226, 125, 230)
CREAM = (255, 244, 214, 255)
DARK = (25, 7, 34, 255)
PANEL = (31, 9, 38, 248)
