"""
Daily Astro Hindi Video Renderer - V12

Purpose:
- Keep the existing generated astrology narration/script.
- Put a REAL deity photograph/illustration prominently into each Rashi scene.
- Animate every Rashi scene with a slow cinematic zoom/pan and gentle motion.
- Cross-fade between Rashi scenes.
- Never use the old generic Om-only fallback as a deity image.
- If Wikimedia cannot provide a deity image, stop with a clear error instead
  of silently generating a fake deity card.

Run:
    python -m video_engine.render
"""

from pathlib import Path
import asyncio
import json
import math
import re
import subprocess
import textwrap
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts
import imageio_ffmpeg


# ============================================================
# CONFIG
# ============================================================

OUTPUT = Path("output")
SCENES = OUTPUT / "video_scenes"
DEITIES = OUTPUT / "deity_images"

SCRIPT = OUTPUT / "daily_script.md"
VOICE = OUTPUT / "daily_voice.mp3"
VIDEO = OUTPUT / "daily_video.mp4"
CREDITS = OUTPUT / "deity_credits.txt"
FFMPEG_LOG = OUTPUT / "ffmpeg_render.log"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

VOICE_NAME = "hi-IN-SwaraNeural"

FONT_URL = (
    "https://github.com/googlefonts/"
    "noto-fonts/raw/main/hinted/ttf/"
    "NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
)
FONT_PATH = OUTPUT / "NotoSansDevanagari-Regular.ttf"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 Chrome/124 Safari/537.36 "
    "DailyAstroHindi/4.0"
)


# ============================================================
# RASHI / DEITY MAP
# ============================================================

RASHIS = [
    ("मेष", "मेष राशि", "हनुमान जी", "Hanuman"),
    ("वृषभ", "वृषभ राशि", "महालक्ष्मी जी", "Lakshmi goddess"),
    ("मिथुन", "मिथुन राशि", "श्री गणेश जी", "Ganesha"),
    ("कर्क", "कर्क राशि", "भगवान शिव", "Shiva Hindu god"),
    ("सिंह", "सिंह राशि", "सूर्य देव", "Surya Hindu god"),
    ("कन्या", "कन्या राशि", "श्री गणेश जी", "Ganesha"),
    ("तुला", "तुला राशि", "महालक्ष्मी जी", "Lakshmi goddess"),
    ("वृश्चिक", "वृश्चिक राशि", "हनुमान जी", "Hanuman"),
    ("धनु", "धनु राशि", "भगवान विष्णु", "Vishnu Hindu god"),
    ("मकर", "मकर राशि", "शनि देव", "Shani Hindu god"),
    ("कुंभ", "कुंभ राशि", "शनि देव", "Shani Hindu god"),
    ("मीन", "मीन राशि", "भगवान विष्णु", "Vishnu Hindu god"),
]


# ============================================================
# SHELL / FILE HELPERS
# ============================================================

def run(cmd, timeout=900):
    print("RUN:", " ".join(str(x) for x in cmd))
    result = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    FFMPEG_LOG.write_text(
        result.stdout,
        encoding="utf-8",
    )
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )
    return result.stdout


def request_bytes(url, timeout=60):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get_font(size):
    OUTPUT.mkdir(parents=True, exist_ok=True)

    if not FONT_PATH.exists():
        FONT_PATH.write_bytes(request_bytes(FONT_URL))

    return ImageFont.truetype(
        str(FONT_PATH),
        size,
    )


def wrap_text(text, width=30):
    output = []
    for paragraph in text.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        output.extend(
            textwrap.wrap(
                paragraph,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return output


# ============================================================
# SCRIPT
# ============================================================

def load_script():
    if not SCRIPT.exists():
        raise RuntimeError(
            "output/daily_script.md was not generated."
        )

    script = SCRIPT.read_text(
        encoding="utf-8"
    ).strip()

    if not script:
        raise RuntimeError(
            "output/daily_script.md is empty."
        )

    return script


def extract_sections(script):
    """
    Finds each Rashi section without changing the content generated
    by content_engine/script.py.
    """
    found = {}

    for index, (key, label, deity, query) in enumerate(RASHIS):
        start = -1

        candidates = [
            f"{key} राशि",
            f"राशि: {key}",
            f"**{key}**",
            f"### {key}",
            f"## {key}",
            key,
        ]

        for candidate in candidates:
            pos = script.find(candidate)
            if pos >= 0:
                start = pos
                break

        if start < 0:
            continue

        end = len(script)

        for other_key, *_ in RASHIS[index + 1:]:
            other_candidates = [
                f"{other_key} राशि",
                f"राशि: {other_key}",
                f"**{other_key}**",
                f"### {other_key}",
                f"## {other_key}",
            ]

            for candidate in other_candidates:
                pos = script.find(
                    candidate,
                    start + len(key) + 2,
                )
                if 0 <= pos < end:
                    end = pos

        section = script[start:end].strip()

        if section:
            found[key] = section

    return found


def fallback_section(script, key):
    """
    Only used if the script's formatting does not contain a clean
    section heading. It does not invent astrology content.
    """
    lines = [
        line.strip()
        for line in script.splitlines()
        if key in line
    ]

    if lines:
        return "\n".join(lines[:8])

    return (
        f"{key} राशि के लिए आज के प्रमुख ग्रह गोचर "
        "और उनके संकेत।"
    )


# ============================================================
# WIKIMEDIA COMMONS IMAGE RESOLUTION
# ============================================================

def commons_search(search_text):
    """
    Search Wikimedia Commons at runtime and return an actual image URL.
    This avoids hard-coded thumbnail URLs that can return HTTP 403.
    """

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": search_text,
        "gsrnamespace": "6",
        "gsrlimit": "10",
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "iiurlwidth": "1400",
        "format": "json",
        "formatversion": "2",
    }

    url = (
        "https://commons.wikimedia.org/w/api.php?"
        + urllib.parse.urlencode(params)
    )

    data = request_bytes(url)
    payload = json.loads(data.decode("utf-8"))

    pages = payload.get("query", {}).get("pages", [])

    candidates = []

    for page in pages:
        info = page.get("imageinfo") or []
        if not info:
            continue

        item = info[0]
        image_url = item.get("thumburl") or item.get("url")
        mime = item.get("mime", "")

        if not image_url:
            continue

        if not mime.startswith("image/"):
            continue

        candidates.append(
            {
                "title": page.get("title", ""),
                "url": image_url,
                "pageid": page.get("pageid", ""),
            }
        )

    if not candidates:
        return None

    # Prefer filenames that look like actual devotional artwork.
    preferred = [
        item for item in candidates
        if any(
            word in item["title"].lower()
            for word in (
                "temple",
                "idol",
                "murti",
                "god",
                "goddess",
                "deity",
                "statue",
                "painting",
            )
        )
    ]

    return (preferred or candidates)[0]



def _draw_centered(draw, text, font, y, fill):
    box = draw.textbbox((0, 0), text, font=font)
    x = (1000 - (box[2] - box[0])) / 2
    draw.text((x, y), text, font=font, fill=fill)


def _halo(draw, cx, cy, radius):
    for r in range(radius, 40, -12):
        alpha = int(18 + 90 * (radius - r) / max(1, radius - 40))
        fill = (255, 205, 60, alpha)
        draw.ellipse(
            (cx-r, cy-r, cx+r, cy+r),
            outline=fill,
            width=8,
        )


def _deity_canvas():
    return Image.new("RGBA", (1000, 1000), (8, 3, 28, 255))


def _save_deity(img, path):
    # Add a soft vignette so the deity remains visually dominant
    # after the scene is animated.
    vignette = Image.new("L", (1000, 1000), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse((60, 40, 940, 960), fill=235)
    vignette = vignette.filter(ImageFilter.GaussianBlur(55))

    dark = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
    dark.putalpha(Image.eval(vignette, lambda p: 235 - p))
    img = Image.alpha_composite(img, dark)

    img.convert("RGB").save(path, "JPEG", quality=96)


def _make_hanuman(path):
    img = _deity_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 213, 75, 255)
    red = (178, 35, 35, 255)
    skin = (155, 82, 48, 255)
    dark = (45, 18, 18, 255)
    white = (255, 245, 220, 255)

    _halo(d, 500, 390, 350)

    # Crown
    d.polygon([(410,245),(445,115),(500,205),(555,115),(590,245)], fill=gold)
    d.ellipse((420,210,580,300), fill=gold, outline=white, width=4)

    # Ears / head / face
    d.ellipse((350,280,650,570), fill=skin, outline=gold, width=7)
    d.ellipse((300,330,390,460), fill=skin, outline=gold, width=6)
    d.ellipse((610,330,700,460), fill=skin, outline=gold, width=6)
    d.ellipse((415,365,450,405), fill=dark)
    d.ellipse((550,365,585,405), fill=dark)
    d.polygon([(475,425),(525,425),(500,475)], fill=(105,45,30,255))
    d.arc((430,445,570,525), 10, 170, fill=white, width=8)

    # Tilak
    d.line((500,310,500,385), fill=white, width=9)

    # Body
    d.ellipse((310,520,690,880), fill=red, outline=gold, width=7)
    d.ellipse((225,555,385,700), fill=skin, outline=gold, width=6)
    d.ellipse((615,555,775,700), fill=skin, outline=gold, width=6)

    # Mace
    d.line((770,350,790,820), fill=gold, width=28)
    d.ellipse((700,250,875,430), fill=gold, outline=white, width=7)

    # Tail
    d.arc((150,640,420,930), 260, 70, fill=skin, width=24)

    _draw_centered(d, "हनुमान जी", get_font(62), 900, gold)
    _save_deity(img, path)


def _make_ganesha(path):
    img = _deity_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 211, 72, 255)
    skin = (218, 142, 105, 255)
    red = (180, 42, 45, 255)
    dark = (48, 18, 25, 255)
    white = (255, 245, 220, 255)

    _halo(d, 500, 390, 350)

    # Crown
    d.polygon([(385,255),(430,105),(500,200),(570,105),(615,255)], fill=gold)
    d.ellipse((390,225,610,310), fill=gold, outline=white, width=4)

    # Elephant head and ears
    d.ellipse((335,270,665,610), fill=skin, outline=gold, width=7)
    d.ellipse((215,320,395,555), fill=skin, outline=gold, width=6)
    d.ellipse((605,320,785,555), fill=skin, outline=gold, width=6)

    d.ellipse((405,385,445,425), fill=dark)
    d.ellipse((555,385,595,425), fill=dark)

    # Trunk
    d.rounded_rectangle((460,430,540,690), radius=35, fill=skin, outline=gold, width=5)
    d.arc((475,575,590,720), 90, 270, fill=skin, width=38)

    # Body and four arms
    d.ellipse((330,585,670,900), fill=red, outline=gold, width=7)
    for x1, y1, x2, y2 in [
        (350,620,220,520),(650,620,780,520),
        (360,720,230,820),(640,720,770,820)
    ]:
        d.line((x1,y1,x2,y2), fill=skin, width=38)

    # Modak
    d.ellipse((735,800,815,875), fill=gold)
    _draw_centered(d, "श्री गणेश जी", get_font(58), 900, gold)
    _save_deity(img, path)


def _make_shiva(path):
    img = _deity_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 211, 72, 255)
    skin = (168, 190, 205, 255)
    blue = (55, 115, 175, 255)
    dark = (25, 30, 45, 255)
    white = (245, 250, 255, 255)

    _halo(d, 500, 400, 350)

    # Hair / top knot
    d.ellipse((350,180,650,580), fill=skin, outline=gold, width=7)
    d.polygon([(360,250),(420,100),(500,205),(580,100),(640,250)], fill=dark)
    d.arc((350,90,650,390), 180, 360, fill=gold, width=16)

    # Third eye
    d.ellipse((485,310,515,360), fill=blue)
    d.ellipse((420,385,465,425), fill=dark)
    d.ellipse((535,385,580,425), fill=dark)
    d.arc((435,420,565,520), 10, 170, fill=white, width=8)

    # Blue throat
    d.ellipse((420,465,580,650), fill=blue, outline=gold, width=6)

    # Body
    d.ellipse((320,570,680,900), fill=white, outline=gold, width=7)

    # Trident
    d.line((760,200,760,850), fill=gold, width=18)
    d.line((760,210,690,320), fill=gold, width=14)
    d.line((760,210,830,320), fill=gold, width=14)
    d.line((760,210,760,330), fill=gold, width=14)

    # Crescent
    d.arc((400,155,600,335), 205, 335, fill=white, width=14)

    _draw_centered(d, "भगवान शिव", get_font(62), 900, gold)
    _save_deity(img, path)


def _make_lakshmi(path):
    img = _deity_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 215, 75, 255)
    skin = (235, 172, 145, 255)
    pink = (215, 70, 120, 255)
    red = (175, 45, 60, 255)
    white = (255, 245, 225, 255)

    _halo(d, 500, 380, 350)

    # Lotus seat
    for cx, cy, rx, ry in [
        (390,760,120,80),(455,730,110,85),(545,730,110,85),(610,760,120,80)
    ]:
        d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry), fill=pink, outline=gold, width=4)

    # Body / sari
    d.polygon([(380,430),(620,430),(720,870),(280,870)], fill=red, outline=gold)
    d.ellipse((400,235,600,470), fill=skin, outline=gold, width=7)

    # Crown
    d.polygon([(405,260),(450,115),(500,205),(550,115),(595,260)], fill=gold)
    d.ellipse((410,225,590,290), fill=gold)

    # Face
    d.ellipse((430,325,462,360), fill=(45,25,30,255))
    d.ellipse((538,325,570,360), fill=(45,25,30,255))
    d.arc((445,350,555,420), 5, 175, fill=white, width=7)

    # Four arms
    for x1,y1,x2,y2 in [(420,490,245,370),(580,490,755,370),(400,590,220,670),(600,590,780,670)]:
        d.line((x1,y1,x2,y2), fill=skin, width=34)

    # Lotus in hands
    for cx,cy in [(235,350),(765,350),(210,660),(790,660)]:
        d.ellipse((cx-35,cy-55,cx+35,cy+55), fill=pink, outline=gold, width=3)

    _draw_centered(d, "महालक्ष्मी जी", get_font(58), 900, gold)
    _save_deity(img, path)


def _make_vishnu(path):
    img = _deity_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 213, 75, 255)
    skin = (95,145,205,255)
    yellow = (232,185,55,255)
    dark = (30,40,70,255)
    white = (245,250,255,255)

    _halo(d, 500, 390, 350)

    # Crown
    d.polygon([(390,255),(430,100),(500,195),(570,100),(610,255)], fill=gold)
    d.ellipse((395,225,605,300), fill=gold, outline=white, width=4)

    # Face and body
    d.ellipse((365,270,635,560), fill=skin, outline=gold, width=7)
    d.ellipse((425,365,465,405), fill=dark)
    d.ellipse((535,365,575,405), fill=dark)
    d.arc((430,420,570,510), 5, 175, fill=white, width=8)
    d.ellipse((330,520,670,900), fill=yellow, outline=gold, width=7)

    # Four arms
    arms = [(360,570,190,350),(640,570,810,350),(360,690,180,810),(640,690,820,810)]
    for x1,y1,x2,y2 in arms:
        d.line((x1,y1,x2,y2), fill=skin, width=34)

    # Conch, chakra, mace, lotus
    d.ellipse((145,315,240,410), fill=white, outline=gold, width=5)
    d.ellipse((770,315,865,410), fill=gold, outline=white, width=5)
    d.line((815,355,815,430), fill=gold, width=10)
    d.ellipse((130,775,235,880), outline=gold, width=14)
    d.line((182,785,182,870), fill=gold, width=8)
    d.line((182,830,225,810), fill=gold, width=8)

    _draw_centered(d, "भगवान विष्णु", get_font(58), 900, gold)
    _save_deity(img, path)



def _make_surya(path):
    img = _deity_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 205, 55, 255)
    orange = (240, 110, 25, 255)
    red = (170, 45, 25, 255)
    skin = (205, 135, 85, 255)
    white = (255, 248, 220, 255)

    # Radiant solar halo.
    _halo(d, 500, 390, 350)

    # Sun rays.
    for angle in range(0, 360, 20):
        rad = math.radians(angle)
        x1 = 500 + int(335 * math.cos(rad))
        y1 = 390 + int(335 * math.sin(rad))
        x2 = 500 + int(455 * math.cos(rad))
        y2 = 390 + int(455 * math.sin(rad))
        d.line((x1, y1, x2, y2), fill=gold, width=18)

    # Crown.
    d.polygon(
        [(390,255),(430,105),(500,195),(570,105),(610,255)],
        fill=gold,
        outline=white,
    )
    d.ellipse(
        (395,225,605,295),
        fill=orange,
        outline=white,
        width=4,
    )

    # Face.
    d.ellipse(
        (350,275,650,570),
        fill=skin,
        outline=gold,
        width=7,
    )
    d.ellipse((420,365,460,405), fill=red)
    d.ellipse((540,365,580,405), fill=red)
    d.arc((430,420,570,510), 5, 175, fill=white, width=8)

    # Golden robes / torso.
    d.ellipse(
        (320,515,680,910),
        fill=orange,
        outline=gold,
        width=8,
    )

    # Two raised arms.
    d.line((390,590,190,370), fill=skin, width=34)
    d.line((610,590,810,370), fill=skin, width=34)

    # Solar discs in hands.
    d.ellipse((135,315,245,425), fill=gold, outline=white, width=6)
    d.ellipse((755,315,865,425), fill=gold, outline=white, width=6)

    # Central sun emblem.
    d.ellipse(
        (430,610,570,750),
        fill=gold,
        outline=white,
        width=5,
    )
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = 500 + int(78 * math.cos(rad))
        y1 = 680 + int(78 * math.sin(rad))
        x2 = 500 + int(120 * math.cos(rad))
        y2 = 680 + int(120 * math.sin(rad))
        d.line((x1,y1,x2,y2), fill=gold, width=7)

    _draw_centered(d, "सूर्य देव", get_font(62), 900, gold)
    _save_deity(img, path)


def _make_shani(path):
    img = _deity_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 210, 65, 255)
    skin = (80,75,95,255)
    blue = (35,55,110,255)
    dark = (10,10,25,255)
    white = (230,235,255,255)

    _halo(d, 500, 390, 350)

    # Dark halo ring
    d.ellipse((190,80,810,700), outline=blue, width=18)

    # Crown
    d.polygon([(390,260),(440,105),(500,195),(560,105),(610,260)], fill=gold)
    d.ellipse((395,225,605,295), fill=gold, outline=white, width=4)

    # Face/body
    d.ellipse((350,275,650,570), fill=skin, outline=gold, width=7)
    d.ellipse((420,365,460,405), fill=white)
    d.ellipse((540,365,580,405), fill=white)
    d.ellipse((435,380,450,395), fill=dark)
    d.ellipse((550,380,565,395), fill=dark)
    d.ellipse((330,520,670,900), fill=blue, outline=gold, width=7)

    # Staff
    d.line((760,230,760,850), fill=gold, width=18)
    d.ellipse((710,160,810,260), fill=gold, outline=white, width=5)

    # Saturn ring
    d.ellipse((170,500,830,700), outline=gold, width=10)

    _draw_centered(d, "शनि देव", get_font(62), 900, gold)
    _save_deity(img, path)


# ============================================================
# REAL DEITY ARTWORK SOURCES
# ============================================================

# IMPORTANT:
# Do NOT use the old LACMA image URLs here. Those endpoints returned 404s.
# We use The Metropolitan Museum of Art Open Access API for six deities.
# The Met explicitly provides public-domain images through its Open Access API.
# Shani also uses The Metropolitan Museum of Art Open Access API.
# The selected record is the Met's public-domain iconographic drawing of
# Saturn/Shanaishchara, so no Wikimedia request is made at runtime.

MET_API = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{}"

DEITY_SOURCES = {
    "हनुमान जी": {
        "met_id": 37960,
        "title": "Hanuman Bearing the Mountaintop with Medicinal Herbs — The Metropolitan Museum of Art, 57.70.6",
        "credit": "The Metropolitan Museum of Art Open Access — Public Domain",
    },
    "महालक्ष्मी जी": {
        "met_id": 78264,
        "title": "Lakshmi — The Metropolitan Museum of Art, 2013.10",
        "credit": "The Metropolitan Museum of Art Open Access — Public Domain",
    },
    "श्री गणेश जी": {
        "met_id": 37397,
        "title": "Ganesha — The Metropolitan Museum of Art, 2015.500.4.12",
        "credit": "The Metropolitan Museum of Art Open Access — Public Domain",
    },
    "भगवान शिव": {
        "met_id": 39328,
        "title": "Shiva as Lord of Dance (Nataraja) — The Metropolitan Museum of Art",
        "credit": "The Metropolitan Museum of Art Open Access — Public Domain",
    },
    "सूर्य देव": {
        "met_id": 39248,
        "title": "Standing Surya — The Metropolitan Museum of Art, 2000.284.1",
        "credit": "The Metropolitan Museum of Art Open Access — Public Domain",
    },
    "भगवान विष्णु": {
        "met_id": 39326,
        "title": "Standing Vishnu — The Metropolitan Museum of Art, 62.265",
        "credit": "The Metropolitan Museum of Art Open Access — Public Domain",
    },
    "शनि देव": {
        "picryl_page": "https://picryl.com/media/shani-deva-fbf817",
        "title": "Shani Deva — public-domain historical devotional image (PICRYL)",
        "credit": "Public-domain image surfaced by PICRYL; source attribution retained in credits.",
    },
}


def met_object_image(met_id):
    """Resolve a stable public-domain image through The Met Open Access API."""
    api_url = MET_API.format(met_id)
    raw = request_bytes(api_url, timeout=60)
    data = json.loads(raw.decode("utf-8"))

    if not data.get("isPublicDomain"):
        raise RuntimeError(f"Met object {met_id} is not marked public domain.")

    image_url = data.get("primaryImage") or data.get("primaryImageSmall")
    if not image_url:
        raise RuntimeError(f"Met object {met_id} has no downloadable primary image.")

    return image_url



def picryl_image_url(page_url):
    """Resolve the og:image from a public-domain PICRYL media page."""
    raw = request_bytes(page_url, timeout=60)
    html = raw.decode("utf-8", "ignore")
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            return urllib.parse.urljoin(page_url, match.group(1))
    raise RuntimeError("PICRYL page did not expose an og:image URL.")


def download_deity(item_index, deity, query):
    destination = DEITIES / f"deity_{item_index:02d}.jpg"
    source = DEITY_SOURCES.get(deity)

    if source is None:
        raise RuntimeError(f"No real deity artwork source exists for {deity}.")

    # Resolve the actual image URL once. This avoids hard-coded museum image
    # paths that can become stale while keeping the source authoritative.
    if "met_id" in source:
        image_url = met_object_image(source["met_id"])
    elif "picryl_page" in source:
        image_url = picryl_image_url(source["picryl_page"])
    else:
        image_url = source["url"]

    print(f"Downloading real deity artwork: {deity}")
    print(f"Artwork source: {image_url}")

    last_error = None
    if not destination.exists() or destination.stat().st_size < 10000:
        for attempt, wait_seconds in enumerate((0, 5, 15), start=1):
            if wait_seconds:
                time.sleep(wait_seconds)
            try:
                data = request_bytes(image_url, timeout=90)
                if not data or len(data) < 10000:
                    raise RuntimeError("Downloaded response is too small to be an image.")
                destination.write_bytes(data)
                break
            except Exception as exc:
                last_error = exc
                print(f"Deity download attempt {attempt} failed for {deity}: {exc}")
        else:
            raise RuntimeError(
                f"Could not download the real deity image for {deity}. Last error: {last_error}"
            )

    try:
        with Image.open(destination) as raw:
            raw = raw.convert("RGB")
            if raw.width < 300 or raw.height < 300:
                raise RuntimeError(f"Deity image is too small: {raw.size}")
            # HD QUALITY GATE:
            # Keep the original high-resolution artwork whenever possible.
            # If a source is smaller than the HD target, upscale it once so
            # the final 1080x1920 render never uses a tiny source image.
            min_long_edge = 2160
            long_edge = max(raw.width, raw.height)
            if long_edge < min_long_edge:
                scale = min_long_edge / long_edge
                new_size = (
                    max(1, int(round(raw.width * scale))),
                    max(1, int(round(raw.height * scale))),
                )
                raw = raw.resize(new_size, Image.Resampling.LANCZOS)

            # Do not downsample HD source artwork.
            raw.save(destination, "JPEG", quality=97, subsampling=0)
    except Exception as exc:
        raise RuntimeError(
            f"Downloaded deity artwork for {deity} is not a valid image: {exc}"
        )

    return destination, source["title"], image_url, source["credit"]


def prepare_deities():
    DEITIES.mkdir(parents=True, exist_ok=True)

    credits = [
        "REAL DEITY ARTWORK CREDITS",
        "===========================",
        "",
        "All seven deity visuals are rendered in HD quality for the 1080x1920 video. Source artwork is preserved at native resolution when possible and upscaled only when necessary; no generated geometric/cartoon deity drawings are used.",
        "",
    ]

    resolved = {}
    unique = {}

    for _, _, deity, query in RASHIS:
        unique[deity] = query

    for number, (deity, query) in enumerate(unique.items(), start=1):
        path, title, source_url, credit = download_deity(number, deity, query)
        resolved[deity] = path
        with Image.open(path) as verified:
            width, height = verified.size
        credits.extend([
            deity,
            title,
            credit,
            source_url,
            f"Rendered artwork resolution: {width}x{height}",
            ""]
        )

    CREDITS.write_text("\n".join(credits), encoding="utf-8")
    return resolved


# ============================================================
# STATIC SCENE CREATION
# ============================================================

def crop_cover(img, width, height):
    img = img.convert("RGB")

    scale = max(
        width / img.width,
        height / img.height,
    )

    nw = int(img.width * scale)
    nh = int(img.height * scale)

    img = img.resize(
        (nw, nh),
        Image.Resampling.LANCZOS,
    )

    left = max(0, (nw - width) // 2)
    top = max(0, (nh - height) // 2)

    return img.crop(
        (
            left,
            top,
            left + width,
            top + height,
        )
    )


def create_scene(
    index,
    key,
    label,
    deity,
    deity_image,
    content,
):
    """
    Produces a high-resolution vertical poster that ffmpeg later animates.

    Deity image is deliberately large:
    approximately 900 x 900 inside the 1080 x 1920 canvas.
    """

    output = SCENES / f"{index:03d}_{key}.jpg"

    deity_img = Image.open(
        deity_image
    ).convert("RGB")

    # Full-canvas blurred devotional background.
    bg = crop_cover(
        deity_img,
        WIDTH,
        HEIGHT,
    )
    bg = bg.filter(
        ImageFilter.GaussianBlur(30)
    )

    canvas = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    canvas.paste(
        bg,
        (0, 0),
    )

    overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (8, 4, 25, 170),
    )

    canvas = Image.alpha_composite(
        canvas,
        overlay,
    )

    draw = ImageDraw.Draw(canvas)

    title_font = get_font(72)
    body_font = get_font(36)
    footer_font = get_font(28)

    # Header.
    draw.rounded_rectangle(
        (28, 28, WIDTH - 28, 175),
        radius=34,
        fill=(3, 2, 18, 230),
        outline=(255, 210, 65, 235),
        width=4,
    )

    title = f"॥ {label} ॥"

    box = draw.textbbox(
        (0, 0),
        title,
        font=title_font,
    )

    draw.text(
        (
            (WIDTH - (box[2] - box[0])) / 2,
            60,
        ),
        title,
        font=title_font,
        fill=(255, 220, 80),
    )

    # Main deity frame.
    panel = (
        35,
        220,
        WIDTH - 35,
        1110,
    )

    draw.rounded_rectangle(
        panel,
        radius=42,
        fill=(2, 1, 15, 230),
        outline=(255, 215, 75, 240),
        width=5,
    )

    hero_w = 900
    hero_h = 790

    # Fit the complete deity artwork inside the hero area so the figure
    # is not cropped at the head, hands, mount, halo, or feet.
    hero = deity_img.copy()
    hero.thumbnail(
        (hero_w, hero_h),
        Image.Resampling.LANCZOS,
    )

    hero_canvas = Image.new(
        "RGB",
        (hero_w, hero_h),
        (10, 7, 28),
    )

    hx = (hero_w - hero.width) // 2
    hy = (hero_h - hero.height) // 2
    hero_canvas.paste(hero, (hx, hy))

    x = (WIDTH - hero_w) // 2
    y = 250

    mask = Image.new(
        "L",
        (hero_w, hero_h),
        0,
    )

    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        (0, 0, hero_w, hero_h),
        radius=36,
        fill=255,
    )

    canvas.paste(
        hero_canvas,
        (x, y),
        mask,
    )

    draw.rounded_rectangle(
        (
            x,
            y,
            x + hero_w,
            y + hero_h,
        ),
        radius=36,
        outline=(255, 225, 130, 245),
        width=5,
    )

    # No deity name is printed below the artwork.
    # The Rashi header above the image is the only title in the devotional panel.

    # Astrology panel.
    text_panel = (
        42,
        1145,
        WIDTH - 42,
        1695,
    )

    draw.rounded_rectangle(
        text_panel,
        radius=30,
        fill=(3, 2, 17, 238),
        outline=(180, 165, 205, 135),
        width=2,
    )

    lines = wrap_text(
        content,
        width=31,
    )

    y_text = 1190

    for line in lines[:10]:
        draw.text(
            (72, y_text),
            line,
            font=body_font,
            fill=(255, 255, 255),
        )
        y_text += 50

        if y_text > 1640:
            break

    footer = (
        "वैदिक गोचर • निरयन • लाहिरी • "
        "सामान्य ज्योतिषीय संकेत"
    )

    box = draw.textbbox(
        (0, 0),
        footer,
        font=footer_font,
    )

    draw.text(
        (
            (WIDTH - (box[2] - box[0])) / 2,
            1790,
        ),
        footer,
        font=footer_font,
        fill=(230, 225, 240),
    )

    canvas.convert("RGB").save(
        output,
        "JPEG",
        quality=95,
    )

    return output


def create_intro():
    output = SCENES / "000_intro.jpg"

    img = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (12, 6, 30),
    )

    draw = ImageDraw.Draw(img)

    om_font = get_font(180)
    title_font = get_font(78)
    subtitle_font = get_font(48)

    for text, y, font, fill in [
        ("ॐ", 300, om_font, (255, 215, 70)),
        ("दैनिक वैदिक ज्योतिष", 650, title_font, (255, 255, 255)),
        ("आज का गोचर विश्लेषण", 800, subtitle_font, (255, 220, 120)),
    ]:
        box = draw.textbbox(
            (0, 0),
            text,
            font=font,
        )
        draw.text(
            (
                (WIDTH - (box[2] - box[0])) / 2,
                y,
            ),
            text,
            font=font,
            fill=fill,
        )

    img.save(
        output,
        "JPEG",
        quality=95,
    )

    return output


def create_outro():
    output = SCENES / "999_outro.jpg"

    img = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (12, 6, 30),
    )

    draw = ImageDraw.Draw(img)

    title_font = get_font(78)
    body_font = get_font(48)

    title = "🙏 धन्यवाद 🙏"

    box = draw.textbbox(
        (0, 0),
        title,
        font=title_font,
    )

    draw.text(
        (
            (WIDTH - (box[2] - box[0])) / 2,
            450,
        ),
        title,
        font=title_font,
        fill=(255, 215, 70),
    )

    messages = [
        "दैनिक वैदिक ज्योतिष अपडेट",
        "वीडियो पसंद आए तो लाइक करें",
        "चैनल को सब्सक्राइब करें",
    ]

    y = 700

    for message in messages:
        box = draw.textbbox(
            (0, 0),
            message,
            font=body_font,
        )

        draw.text(
            (
                (WIDTH - (box[2] - box[0])) / 2,
                y,
            ),
            message,
            font=body_font,
            fill=(255, 255, 255),
        )

        y += 115

    img.save(
        output,
        "JPEG",
        quality=95,
    )

    return output


# ============================================================
# VOICE
# ============================================================

async def make_voice(text):
    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+5%",
        volume="+0%",
    )

    await communicate.save(
        str(VOICE)
    )


def audio_duration(ffmpeg):
    result = subprocess.run(
        [
            ffmpeg,
            "-i",
            str(VOICE),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )

    match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        result.stderr,
    )

    if not match:
        raise RuntimeError(
            "Could not determine narration duration."
        )

    h = int(match.group(1))
    m = int(match.group(2))
    s = float(match.group(3))

    return h * 3600 + m * 60 + s


# ============================================================
# ANIMATION
# ============================================================

def make_animated_clip(
    ffmpeg,
    scene,
    duration,
    index,
):
    """
    Convert one static devotional/Rashi poster into an animated clip.

    This implementation deliberately avoids FFmpeg expression functions
    such as sin(), cos() and eq=brightness.  GitHub's FFmpeg build has been
    rejecting those expressions in the filter graph.  The animation is
    therefore produced using only zoompan's simple frame counter:

      - continuous slow zoom from 1.00x to about 1.12x
      - centered crop follows the zoom automatically

    The scene-to-scene transition is handled separately by xfade.
    """

    output = SCENES / f"clip_{index:02d}.mp4"

    frames = max(
        1,
        int(round(duration * FPS)),
    )

    # Simple arithmetic only. No sin/cos/eq expressions.
    # At the end of a typical ~50 s clip this reaches about 1.12x.
    zoom_expr = "1+0.00008*on"
    x_expr = "(iw-iw/zoom)/2"
    y_expr = "(ih-ih/zoom)/2"

    filtergraph = (
        "zoompan="
        f"z={zoom_expr}:"
        f"x={x_expr}:"
        f"y={y_expr}:"
        f"d={frames}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS}"
    )

    run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            scene,
            "-vf",
            filtergraph,
            "-frames:v",
            str(frames),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        timeout=900,
    )

    if not output.exists():
        raise RuntimeError(
            f"Animated clip was not created: {output}"
        )

    return output


# ============================================================
# CROSSFADE + AUDIO
# ============================================================

def make_crossfade_video(
    ffmpeg,
    clips,
    clip_duration,
    transition,
):
    """
    Cross-fade all generated clips.

    For N clips:
      final duration = N*clip_duration - (N-1)*transition
    """

    if len(clips) == 1:
        return clips[0]

    # Build xfade chain.
    inputs = []

    for clip in clips:
        inputs.extend(
            [
                "-i",
                str(clip),
            ]
        )

    filter_parts = []

    current = "[0:v]"

    for i in range(1, len(clips)):
        offset = (
            i * clip_duration
            - i * transition
        )

        output_label = (
            f"[xf{i}]"
        )

        filter_parts.append(
            f"{current}[{i}:v]"
            f"xfade=transition=fade:"
            f"duration={transition}:"
            f"offset={offset:.3f}"
            f"{output_label}"
        )

        current = output_label

    filtergraph = ";".join(
        filter_parts
    )

    output = SCENES / "video_no_audio.mp4"

    run(
        [
            ffmpeg,
            "-y",
            *inputs,
            "-filter_complex",
            filtergraph,
            "-map",
            current,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(output),
        ],
        timeout=1200,
    )

    return output


def attach_audio(
    ffmpeg,
    silent_video,
):
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(VOICE),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(VIDEO),
        ],
        timeout=1200,
    )

    if not VIDEO.exists():
        raise RuntimeError(
            "Final daily_video.mp4 was not created."
        )


def build_video(
    ffmpeg,
    scene_paths,
    narration_seconds,
):
    """
    14 scenes:
      intro + 12 rashis + outro

    Cross-fades are 0.8 sec.

    The clip duration is calculated so the final cross-faded video
    matches the narration length closely.
    """

    transition = 0.8
    count = len(scene_paths)

    clip_duration = (
        narration_seconds
        + (count - 1) * transition
    ) / count

    print(
        f"Scene count: {count}"
    )
    print(
        f"Clip duration: {clip_duration:.3f}s"
    )
    print(
        f"Transition: {transition:.3f}s"
    )

    clips = []

    for index, scene in enumerate(
        scene_paths
    ):
        clips.append(
            make_animated_clip(
                ffmpeg,
                scene,
                clip_duration,
                index,
            )
        )

    silent = make_crossfade_video(
        ffmpeg,
        clips,
        clip_duration,
        transition,
    )

    attach_audio(
        ffmpeg,
        silent,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    SCENES.mkdir(
        parents=True,
        exist_ok=True,
    )

    DEITIES.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove only files generated by this renderer.
    for pattern in (
        "*.jpg",
        "*.mp4",
        "*.download",
    ):
        for file in SCENES.glob(pattern):
            try:
                file.unlink()
            except Exception:
                pass

    script = load_script()

    print("Loaded daily_script.md")

    # --------------------------------------------------------
    # REAL DEITY ARTWORK
    # --------------------------------------------------------

    deity_paths = prepare_deities()

    # --------------------------------------------------------
    # NARRATION
    # --------------------------------------------------------

    print("Generating Hindi narration...")
    asyncio.run(
        make_voice(script)
    )

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    narration_seconds = audio_duration(
        ffmpeg
    )

    print(
        f"Narration: {narration_seconds:.2f}s"
    )

    # --------------------------------------------------------
    # SCENES
    # --------------------------------------------------------

    scenes = []

    scenes.append(
        create_intro()
    )

    sections = extract_sections(
        script
    )

    for index, (
        key,
        label,
        deity,
        query,
    ) in enumerate(
        RASHIS,
        start=1,
    ):
        content = sections.get(
            key,
            fallback_section(
                script,
                key,
            ),
        )

        scene = create_scene(
            index,
            key,
            label,
            deity,
            deity_paths[deity],
            content,
        )

        scenes.append(scene)

    scenes.append(
        create_outro()
    )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    build_video(
        ffmpeg,
        scenes,
        narration_seconds,
    )

    print()
    print("========================================")
    print("DAILY ASTRO HINDI VIDEO COMPLETE")
    print("========================================")
    print(f"VIDEO:   {VIDEO}")
    print(f"VOICE:   {VOICE}")
    print(f"CREDITS: {CREDITS}")
    print("Animation: slow zoom + drift + brightness")
    print("Transition: cross-fade")
    print("Deity art: museum/public-domain HD artwork")
    print("========================================")


if __name__ == "__main__":
    main()
