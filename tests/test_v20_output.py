"""Output-level visual and structural QA for AstroPratidin V20."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
SCENES = OUT / "video_scenes"
LOGO = ROOT / "assets" / "brand" / "astropratidin_logo_256.png"
KEYS = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
SCENES_EXPECTED = [SCENES / "000_intro.jpg"] + [SCENES / f"{i:03d}_{k}.jpg" for i, k in enumerate(KEYS, 1)] + [SCENES / "013_outro.jpg"]

assert LOGO.exists(), "Approved AstroPratidin logo is missing"
assert hashlib.sha256(LOGO.read_bytes()).hexdigest() == "419b276c31a386070d2f806e57691e632a123098a920db98b62206d268106b80"
assert len(SCENES_EXPECTED) == 14

with Image.open(LOGO).convert("RGBA") as logo:
    expected_logo = ImageOps.contain(logo, (190, 190), Image.Resampling.LANCZOS)
    for p in SCENES_EXPECTED:
        assert p.exists(), f"Missing scene: {p.name}"
        with Image.open(p).convert("RGB") as im:
            assert im.size == (1080, 1920), f"Wrong scene dimensions: {p.name}: {im.size}"
            # Logo is centered in the protected header: x=445, y=38, 190x190.
            crop = im.crop((445, 38, 635, 228)).convert("RGB")
            expected = Image.new("RGB", (190, 190), (24, 7, 34))
            expected_rgba = Image.new("RGBA", (190, 190), (24, 7, 34, 255))
            expected_rgba.alpha_composite(expected_logo, (0, 0))
            expected = expected_rgba.convert("RGB")
            diff = ImageChops.difference(crop, expected)
            stat = diff.resize((1, 1)).getpixel((0, 0))
            mean_diff = sum(stat) / 3
            assert mean_diff < 32, f"Logo/header mismatch in {p.name}: mean diff {mean_diff:.1f}"

manifest = OUT / "sync_manifest.json"
assert manifest.exists(), "Missing sync_manifest.json"
data = json.loads(manifest.read_text(encoding="utf-8"))
segments = data.get("segments", [])
assert len(segments) == 14, f"Expected 14 sync segments, got {len(segments)}"

video = OUT / "daily_video.mp4"
voice = OUT / "daily_voice.mp3"
assert video.exists() and video.stat().st_size > 1_000_000
assert voice.exists() and voice.stat().st_size > 100_000

print("V20 OUTPUT QA: PASS")
print("14 scenes / 1080x1920: PASS")
print("Exact approved AstroPratidin logo SHA: PASS")
print("Logo placement + pixel match on all 14 scenes: PASS")
print("14-segment synchronization manifest: PASS")
print("Production video/audio: PASS")
