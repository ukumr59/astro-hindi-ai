"""
DAILY VEDIC ASTROLOGY VIDEO ENGINE

Vedic / Jyotisha visual renderer.

Input:
    output/daily_script.md

Output:
    output/daily_video.mp4
    output/daily_voice.mp3
    output/deity_credits.txt

Video:
    1080 x 1920
    Hindi narration
    12 Rashi scenes
    Prominent devotional deity visual
    Intro + Rashi scenes + CTA

IMPORTANT:
    Deity artwork uses direct Wikimedia upload URLs.
    No Wikimedia Special:Redirect endpoint is used.
"""

from pathlib import Path
import asyncio
import subprocess
import textwrap
import urllib.request
import re
import time
import hashlib

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts
import imageio_ffmpeg


# ============================================================
# PATHS
# ============================================================

OUTPUT = Path("output")
SCENES = OUTPUT / "video_scenes"
DEITIES = OUTPUT / "deity_images"

SCRIPT = OUTPUT / "daily_script.md"
VOICE = OUTPUT / "daily_voice.mp3"
VIDEO = OUTPUT / "daily_video.mp4"
CREDITS = OUTPUT / "deity_credits.txt"


# ============================================================
# VIDEO
# ============================================================

WIDTH = 1080
HEIGHT = 1920
FPS = 30

VOICE_NAME = "hi-IN-SwaraNeural"


# ============================================================
# DEITY CONFIGURATION
#
# Direct upload.wikimedia.org URLs are used.
# This avoids Wikimedia Special:Redirect 403 errors.
# ============================================================

RASHIS = [

    {
        "name": "मेष",
        "emoji": "♈",
        "deity": "हनुमान जी",
        "image": "hanuman.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "b/b4/Hanuman%201.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Hanuman_1.jpg"
        ),
        "license": "CC BY-SA 4.0",
    },

    {
        "name": "वृषभ",
        "emoji": "♉",
        "deity": "महालक्ष्मी जी",
        "image": "lakshmi.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "d/dd/Shreelaxmi.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Shreelaxmi.jpg"
        ),
        "license": "Wikimedia Commons - see source",
    },

    {
        "name": "मिथुन",
        "emoji": "♊",
        "deity": "श्री गणेश जी",
        "image": "ganesh.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "9/93/Ganesh%20with%20Garland.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Ganesh_with_Garland.jpg"
        ),
        "license": "Wikimedia Commons - see source",
    },

    {
        "name": "कर्क",
        "emoji": "♋",
        "deity": "भगवान शिव",
        "image": "shiva.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "5/59/Shiv%207.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Shiv_7.jpg"
        ),
        "license": "Wikimedia Commons - see source",
    },

    {
        "name": "सिंह",
        "emoji": "♌",
        "deity": "सूर्य देव",
        "image": "surya.webp",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "f/f6/"
            "%E0%A4%B8%E0%A5%82%E0%A4%B0%E0%A5%8D%E0%A4%AF"
            "%20%E0%A4%A6%E0%A5%87%E0%A4%B5"
            "%20%E0%A4%AE%E0%A5%82%E0%A4%B0%E0%A5%8D%E0%A4%A4%E0%A4%BF"
            "%20%28Sun%20God%20Idol%29.webp"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:%E0%A4%B8%E0%A5%82%E0%A4%B0%E0%A5%8D%E0%A4%AF"
            "_%E0%A4%A6%E0%A5%87%E0%A4%B5_%E0%A4%AE%E0%A5%82%E0%A4%B0%E0%A5%8D%E0%A4%A4%E0%A4%BF"
            "_(Sun_God_Idol).webp"
        ),
        "license": "Wikimedia Commons - see source",
    },

    {
        "name": "कन्या",
        "emoji": "♍",
        "deity": "श्री गणेश जी",
        "image": "ganesh.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "9/93/Ganesh%20with%20Garland.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Ganesh_with_Garland.jpg"
        ),
        "license": "Wikimedia Commons - see source",
    },

    {
        "name": "तुला",
        "emoji": "♎",
        "deity": "महालक्ष्मी जी",
        "image": "lakshmi.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "d/dd/Shreelaxmi.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Shreelaxmi.jpg"
        ),
        "license": "Wikimedia Commons - see source",
    },

    {
        "name": "वृश्चिक",
        "emoji": "♏",
        "deity": "हनुमान जी",
        "image": "hanuman.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "b/b4/Hanuman%201.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Hanuman_1.jpg"
        ),
        "license": "CC BY-SA 4.0",
    },

    {
        "name": "धनु",
        "emoji": "♐",
        "deity": "भगवान विष्णु",
        "image": "vishnu.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "e/e7/"
            "Hand-drawn%20image%20of%20Vishnu%2C%20Mogao%20Caves.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Hand-drawn_image_of_Vishnu,_Mogao_Caves.jpg"
        ),
        "license": "CC0",
    },

    {
        "name": "मकर",
        "emoji": "♑",
        "deity": "शनि देव",
        "image": "shani.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "4/4a/Shani.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Shani.jpg"
        ),
        "license": "Public Domain",
    },

    {
        "name": "कुंभ",
        "emoji": "♒",
        "deity": "शनि देव",
        "image": "shani.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "4/4a/Shani.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Shani.jpg"
        ),
        "license": "Public Domain",
    },

    {
        "name": "मीन",
        "emoji": "♓",
        "deity": "भगवान विष्णु",
        "image": "vishnu.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/"
            "e/e7/"
            "Hand-drawn%20image%20of%20Vishnu%2C%20Mogao%20Caves.jpg"
        ),
        "source": (
            "https://commons.wikimedia.org/wiki/"
            "File:Hand-drawn_image_of_Vishnu,_Mogao_Caves.jpg"
        ),
        "license": "CC0",
    },
]


# ============================================================
# FONT
# ============================================================

FONT_URL = (
    "https://github.com/googlefonts/"
    "noto-fonts/raw/main/hinted/ttf/"
    "NotoSansDevanagari/"
    "NotoSansDevanagari-Regular.ttf"
)

FONT_PATH = OUTPUT / "NotoSansDevanagari-Regular.ttf"


# ============================================================
# FONT
# ============================================================

def get_font(size):

    if not FONT_PATH.exists():

        print("Downloading Devanagari font...")

        request = urllib.request.Request(
            FONT_URL,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(compatible; AstroHindiVideo/1.0)"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            FONT_PATH.write_bytes(
                response.read()
            )

    return ImageFont.truetype(
        str(FONT_PATH),
        size
    )


# ============================================================
# COMMAND
# ============================================================

def run(command, timeout=600):

    print(
        "RUN:",
        " ".join(
            str(x)
            for x in command
        )
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout
    )

    print(result.stdout)

    if result.returncode != 0:

        raise RuntimeError(
            "Command failed with exit code "
            f"{result.returncode}"
        )


# ============================================================
# SCRIPT
# ============================================================

def read_script():

    if not SCRIPT.exists():

        raise RuntimeError(
            "output/daily_script.md was not generated."
        )

    text = SCRIPT.read_text(
        encoding="utf-8"
    ).strip()

    if not text:

        raise RuntimeError(
            "daily_script.md is empty."
        )

    return text


# ============================================================
# DOWNLOAD WITH RETRY
# ============================================================

def download_file(
    url,
    destination,
    retries=3
):

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "Chrome/124.0 Safari/537.36",
        "Accept":
            "image/avif,image/webp,image/apng,"
            "image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language":
            "en-US,en;q=0.9",
    }

    for attempt in range(
        1,
        retries + 1
    ):

        try:

            print(
                f"Downloading artwork "
                f"(attempt {attempt}/{retries})"
            )

            request = urllib.request.Request(
                url,
                headers=headers
            )

            with urllib.request.urlopen(
                request,
                timeout=60
            ) as response:

                data = response.read()

            if not data:

                raise RuntimeError(
                    "Downloaded file is empty."
                )

            destination.write_bytes(
                data
            )

            # Validate image.
            with Image.open(
                destination
            ) as test_image:

                test_image.verify()

            print(
                f"Downloaded successfully: "
                f"{destination}"
            )

            return True

        except Exception as error:

            print(
                f"Download failed: {error}"
            )

            if destination.exists():

                try:
                    destination.unlink()
                except Exception:
                    pass

            if attempt < retries:

                time.sleep(
                    attempt * 2
                )

    return False


# ============================================================
# FALLBACK DEVOTIONAL ART
# ============================================================

def create_deity_fallback(
    deity,
    destination
):

    print(
        f"Creating devotional fallback card "
        f"for {deity}"
    )

    image = Image.new(
        "RGB",
        (900, 1200),
        (16, 7, 40)
    )

    draw = ImageDraw.Draw(
        image
    )

    huge_font = get_font(
        150
    )

    title_font = get_font(
        72
    )

    subtitle_font = get_font(
        44
    )

    # Om
    om = "ॐ"

    bbox = draw.textbbox(
        (0, 0),
        om,
        font=huge_font
    )

    draw.text(
        (
            (900 - (bbox[2] - bbox[0])) / 2,
            170
        ),
        om,
        font=huge_font,
        fill=(255, 215, 80)
    )

    # Deity
    bbox = draw.textbbox(
        (0, 0),
        deity,
        font=title_font
    )

    draw.text(
        (
            (900 - (bbox[2] - bbox[0])) / 2,
            500
        ),
        deity,
        font=title_font,
        fill=(255, 255, 255)
    )

    text = "दिव्य संरक्षण • शुभ ऊर्जा"

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=subtitle_font
    )

    draw.text(
        (
            (900 - (bbox[2] - bbox[0])) / 2,
            650
        ),
        text,
        font=subtitle_font,
        fill=(255, 220, 130)
    )

    image.save(
        destination,
        quality=95
    )


# ============================================================
# DOWNLOAD ALL DEITIES
# ============================================================

def download_deity_images():

    DEITIES.mkdir(
        parents=True,
        exist_ok=True
    )

    unique = {}

    for item in RASHIS:

        unique[
            item["image"]
        ] = item

    credits = []

    for filename, item in unique.items():

        destination = (
            DEITIES / filename
        )

        if destination.exists():

            print(
                f"Artwork already exists: "
                f"{filename}"
            )

            continue

        success = download_file(
            item["url"],
            destination
        )

        if not success:

            print(
                f"WARNING: Could not download "
                f"{item['deity']} artwork."
            )

            # Do NOT stop the entire video.
            create_deity_fallback(
                item["deity"],
                destination
            )

            credits.append(
                f"{item['deity']} - "
                "Fallback devotional artwork generated "
                "locally because source artwork could "
                "not be downloaded.\n"
            )

        else:

            credits.append(
                f"{item['deity']}\n"
                f"Source: {item['source']}\n"
                f"License: {item['license']}\n"
                f"Image URL: {item['url']}\n\n"
            )

    with CREDITS.open(
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "DEVOTIONAL ARTWORK CREDITS\n"
        )

        f.write(
            "===========================\n\n"
        )

        for credit in credits:

            f.write(
                credit
            )


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(
    text,
    width=28
):

    result = []

    for paragraph in text.splitlines():

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        result.extend(
            textwrap.wrap(
                paragraph,
                width=width
            )
        )

    return result


# ============================================================
# RASHI SECTION DETECTION
# ============================================================

def find_rashi_sections(
    script
):

    sections = {}

    for index, rashi in enumerate(
        RASHIS
    ):

        name = rashi["name"]

        patterns = [
            f"{name} राशि",
            f"राशि: {name}",
            f"**{name}**",
            f"### {name}",
            f"## {name}",
        ]

        start = -1

        for pattern in patterns:

            position = script.find(
                pattern
            )

            if position >= 0:

                start = position
                break

        if start < 0:
            continue

        end = len(script)

        for other in RASHIS:

            if other["name"] == name:
                continue

            other_patterns = [
                f"{other['name']} राशि",
                f"राशि: {other['name']}",
                f"**{other['name']}**",
                f"### {other['name']}",
                f"## {other['name']}",
            ]

            for pattern in other_patterns:

                position = script.find(
                    pattern,
                    start + len(name) + 2
                )

                if (
                    position >= 0
                    and position < end
                ):

                    end = position

        section = script[
            start:end
        ].strip()

        if section:

            sections[name] = section

    return sections


# ============================================================
# FALLBACK RASHI CONTENT
# ============================================================

def fallback_section(
    rashi,
    script
):

    matches = []

    for line in script.splitlines():

        if rashi["name"] in line:

            clean = line.strip()

            if clean:

                matches.append(
                    clean
                )

    if matches:

        return "\n".join(
            matches[:8]
        )

    return (
        f"{rashi['name']} राशि के लिए "
        "आज के ग्रह गोचर के सामान्य संकेत।"
    )


# ============================================================
# CREATE INTRO
# ============================================================

def create_intro():

    path = (
        SCENES /
        "000_intro.jpg"
    )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (10, 5, 28)
    )

    draw = ImageDraw.Draw(
        image
    )

    om_font = get_font(
        150
    )

    title_font = get_font(
        78
    )

    subtitle_font = get_font(
        48
    )

    small_font = get_font(
        34
    )

    text = "ॐ"

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=om_font
    )

    draw.text(
        (
            (WIDTH - bbox[2]) / 2,
            300
        ),
        text,
        font=om_font,
        fill=(255, 215, 80)
    )

    title = "दैनिक वैदिक ज्योतिष"

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            600
        ),
        title,
        font=title_font,
        fill=(255, 255, 255)
    )

    subtitle = "आज का गोचर विश्लेषण"

    bbox = draw.textbbox(
        (0, 0),
        subtitle,
        font=subtitle_font
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            750
        ),
        subtitle,
        font=subtitle_font,
        fill=(255, 220, 130)
    )

    footer = (
        "निरयन • लाहिरी • चंद्र राशि"
    )

    bbox = draw.textbbox(
        (0, 0),
        footer,
        font=small_font
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            1500
        ),
        footer,
        font=small_font,
        fill=(220, 215, 235)
    )

    image.save(
        path,
        quality=95
    )

    return path


# ============================================================
# CREATE RASHI SCENE
# ============================================================

def create_rashi_scene(
    rashi,
    content,
    output_path
):

    image_path = (
        DEITIES /
        rashi["image"]
    )

    deity_image = Image.open(
        image_path
    ).convert("RGB")

    # --------------------------------------------------------
    # Dark devotional background
    # --------------------------------------------------------

    background = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (12, 5, 30)
    )

    blurred = deity_image.copy()

    blurred.thumbnail(
        (WIDTH, HEIGHT)
    )

    background.paste(
        blurred,
        (
            (WIDTH - blurred.width) // 2,
            (HEIGHT - blurred.height) // 2
        )
    )

    background = background.filter(
        ImageFilter.GaussianBlur(
            radius=22
        )
    )

    dark = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 165)
    )

    background = Image.alpha_composite(
        background.convert("RGBA"),
        dark
    ).convert("RGB")

    draw = ImageDraw.Draw(
        background
    )

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    title_font = get_font(
        76
    )

    deity_font = get_font(
        48
    )

    body_font = get_font(
        39
    )

    footer_font = get_font(
        29
    )

    # --------------------------------------------------------
    # Rashi title
    # --------------------------------------------------------

    title = (
        f"{rashi['emoji']} "
        f"{rashi['name']} राशि"
    )

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            75
        ),
        title,
        font=title_font,
        fill=(255, 215, 80)
    )

    # --------------------------------------------------------
    # Deity panel
    # --------------------------------------------------------

    panel_top = 235
    panel_bottom = 900

    draw.rounded_rectangle(
        (
            45,
            panel_top,
            WIDTH - 45,
            panel_bottom
        ),
        radius=38,
        fill=(4, 2, 18),
        outline=(255, 215, 80),
        width=4
    )

    # --------------------------------------------------------
    # Deity image
    # --------------------------------------------------------

    deity = Image.open(
        image_path
    ).convert("RGB")

    max_width = 620
    max_height = 560

    deity.thumbnail(
        (
            max_width,
            max_height
        )
    )

    deity_x = (
        WIDTH - deity.width
    ) // 2

    deity_y = (
        panel_top
        + 25
        + (
            max_height
            - deity.height
        ) // 2
    )

    background.paste(
        deity,
        (
            deity_x,
            deity_y
        )
    )

    # --------------------------------------------------------
    # Deity name
    # --------------------------------------------------------

    deity_label = (
        f"॥ {rashi['deity']} ॥"
    )

    bbox = draw.textbbox(
        (0, 0),
        deity_label,
        font=deity_font
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            835
        ),
        deity_label,
        font=deity_font,
        fill=(255, 242, 200)
    )

    # --------------------------------------------------------
    # Astrology information
    # --------------------------------------------------------

    content_top = 970
    content_bottom = 1660

    draw.rounded_rectangle(
        (
            50,
            content_top,
            WIDTH - 50,
            content_bottom
        ),
        radius=32,
        fill=(4, 2, 18)
    )

    lines = wrap_text(
        content,
        width=29
    )

    y = content_top + 48

    for line in lines[:12]:

        draw.text(
            (
                85,
                y
            ),
            line,
            font=body_font,
            fill=(255, 255, 255)
        )

        y += 61

        if y > 1580:
            break

    # --------------------------------------------------------
    # Bottom identity
    # --------------------------------------------------------

    footer = (
        "वैदिक गोचर • निरयन • लाहिरी"
    )

    bbox = draw.textbbox(
        (0, 0),
        footer,
        font=footer_font
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            1790
        ),
        footer,
        font=footer_font,
        fill=(225, 220, 240)
    )

    background.save(
        output_path,
        quality=95
    )


# ============================================================
# FINAL SCENE
# ============================================================

def create_final():

    path = (
        SCENES /
        "999_final.jpg"
    )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (10, 5, 28)
    )

    draw = ImageDraw.Draw(
        image
    )

    title_font = get_font(
        78
    )

    body_font = get_font(
        46
    )

    small_font = get_font(
        32
    )

    title = "🙏 धन्यवाद"

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            400
        ),
        title,
        font=title_font,
        fill=(255, 215, 80)
    )

    messages = [
        "दैनिक वैदिक ज्योतिष अपडेट",
        "वीडियो पसंद आए तो लाइक करें",
        "चैनल को सब्सक्राइब करें",
    ]

    y = 650

    for message in messages:

        bbox = draw.textbbox(
            (0, 0),
            message,
            font=body_font
        )

        draw.text(
            (
                (WIDTH - (bbox[2] - bbox[0])) / 2,
                y
            ),
            message,
            font=body_font,
            fill=(255, 255, 255)
        )

        y += 115

    disclaimer = (
        "यह प्रस्तुति पारंपरिक वैदिक ज्योतिषीय "
        "गोचर सिद्धांतों पर आधारित सामान्य जानकारी है।"
    )

    lines = textwrap.wrap(
        disclaimer,
        width=35
    )

    y = 1250

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=small_font
        )

        draw.text(
            (
                (WIDTH - (bbox[2] - bbox[0])) / 2,
                y
            ),
            line,
            font=small_font,
            fill=(210, 205, 225)
        )

        y += 55

    image.save(
        path,
        quality=95
    )

    return path


# ============================================================
# HINDI VOICE
# ============================================================

async def create_voice(
    text
):

    print(
        "Generating Hindi narration..."
    )

    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+5%",
        volume="+0%"
    )

    await communicate.save(
        str(VOICE)
    )

    if not VOICE.exists():

        raise RuntimeError(
            "Hindi voice was not created."
        )


# ============================================================
# AUDIO DURATION
# ============================================================

def get_audio_duration(
    ffmpeg
):

    result = subprocess.run(
        [
            ffmpeg,
            "-i",
            str(VOICE)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60
    )

    output = result.stderr

    match = re.search(
        r"Duration:\s*"
        r"(\d+):(\d+):(\d+(?:\.\d+)?)",
        output
    )

    if not match:

        raise RuntimeError(
            "Could not determine audio duration."
        )

    hours = int(
        match.group(1)
    )

    minutes = int(
        match.group(2)
    )

    seconds = float(
        match.group(3)
    )

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


# ============================================================
# BUILD VIDEO
# ============================================================

def build_video(
    ffmpeg,
    scene_files,
    duration
):

    print(
        "Building scene-based video..."
    )

    intro = scene_files[0]

    final = scene_files[-1]

    rashi_files = scene_files[1:-1]

    intro_duration = min(
        10.0,
        duration * 0.03
    )

    final_duration = min(
        10.0,
        duration * 0.03
    )

    remaining = (
        duration
        - intro_duration
        - final_duration
    )

    if remaining <= 0:

        raise RuntimeError(
            "Invalid narration duration."
        )

    rashi_duration = (
        remaining /
        max(
            1,
            len(rashi_files)
        )
    )

    concat_file = (
        SCENES /
        "video_concat.txt"
    )

    with concat_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        def add(
            path,
            seconds
        ):

            resolved = (
                str(
                    path.resolve()
                )
                .replace(
                    "'",
                    "'\\''"
                )
            )

            f.write(
                f"file '{resolved}'\n"
            )

            f.write(
                f"duration {seconds:.3f}\n"
            )

        add(
            intro,
            intro_duration
        )

        for scene in rashi_files:

            add(
                scene,
                rashi_duration
            )

        add(
            final,
            final_duration
        )

        resolved = (
            str(
                final.resolve()
            )
            .replace(
                "'",
                "'\\''"
            )
        )

        f.write(
            f"file '{resolved}'\n"
        )

    silent_video = (
        SCENES /
        "silent_video.mp4"
    )

    # --------------------------------------------------------
    # Render images into video
    # --------------------------------------------------------

    run([
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-vf",
        (
            f"scale={WIDTH}:{HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:"
            "(ow-iw)/2:(oh-ih)/2"
        ),
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(silent_video)
    ])

    # --------------------------------------------------------
    # Add narration
    # --------------------------------------------------------

    run([
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
        str(VIDEO)
    ])

    if not VIDEO.exists():

        raise RuntimeError(
            "daily_video.mp4 was not created."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    SCENES.mkdir(
        parents=True,
        exist_ok=True
    )

    DEITIES.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Clean previous scenes
    # --------------------------------------------------------

    for file in SCENES.glob(
        "*.jpg"
    ):

        try:
            file.unlink()
        except Exception:
            pass

    for file in SCENES.glob(
        "*.mp4"
    ):

        try:
            file.unlink()
        except Exception:
            pass

    concat = (
        SCENES /
        "video_concat.txt"
    )

    if concat.exists():

        concat.unlink()

    # --------------------------------------------------------
    # Load script
    # --------------------------------------------------------

    script = read_script()

    print(
        "Astrology script loaded."
    )

    # --------------------------------------------------------
    # Download deity artwork
    # --------------------------------------------------------

    print(
        "Preparing devotional artwork..."
    )

    download_deity_images()

    # --------------------------------------------------------
    # Hindi narration
    # --------------------------------------------------------

    asyncio.run(
        create_voice(
            script
        )
    )

    # --------------------------------------------------------
    # Intro
    # --------------------------------------------------------

    scene_files = []

    scene_files.append(
        create_intro()
    )

    # --------------------------------------------------------
    # Rashi sections
    # --------------------------------------------------------

    sections = find_rashi_sections(
        script
    )

    print(
        f"Detected {len(sections)} "
        f"explicit Rashi sections."
    )

    # Always create all 12 Rashi scenes.
    # This guarantees a complete daily video.
    # --------------------------------------------------------

    for index, rashi in enumerate(
        RASHIS,
        start=1
    ):

        content = sections.get(
            rashi["name"]
        )

        if not content:

            content = fallback_section(
                rashi,
                script
            )

        scene_path = (
            SCENES /
            f"{index:03d}_{rashi['name']}.jpg"
        )

        print(
            f"Creating "
            f"{index}/12: "
            f"{rashi['name']} "
            f"→ "
            f"{rashi['deity']}"
        )

        create_rashi_scene(
            rashi,
            content,
            scene_path
        )

        scene_files.append(
            scene_path
        )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    scene_files.append(
        create_final()
    )

    # --------------------------------------------------------
    # Bundled FFmpeg
    # --------------------------------------------------------

    ffmpeg = (
        imageio_ffmpeg.get_ffmpeg_exe()
    )

    print(
        f"FFmpeg: {ffmpeg}"
    )

    # --------------------------------------------------------
    # Audio duration
    # --------------------------------------------------------

    duration = get_audio_duration(
        ffmpeg
    )

    print(
        f"Narration duration: "
        f"{duration:.2f} seconds"
    )

    # --------------------------------------------------------
    # Video
    # --------------------------------------------------------

    build_video(
        ffmpeg,
        scene_files,
        duration
    )

    print()
    print(
        "=========================================="
    )
    print(
        "VEDIC ASTROLOGY VIDEO COMPLETE"
    )
    print(
        "=========================================="
    )
    print(
        f"VIDEO   : {VIDEO}"
    )
    print(
        f"VOICE   : {VOICE}"
    )
    print(
        f"CREDITS : {CREDITS}"
    )
    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()
