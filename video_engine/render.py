"""
Daily Vedic Astrology Video Renderer
------------------------------------
Complete replacement for video_engine/render.py.

Keeps the existing astrology/content pipeline independent and focuses on
rendering a prominent devotional deity visual for every Rashi scene.

Output:
    output/daily_video.mp4
    output/daily_voice.mp3
    output/deity_credits.txt
"""

from pathlib import Path
import asyncio
import subprocess
import textwrap
import urllib.request
import time
import re

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts
import imageio_ffmpeg


# ============================================================
# PATHS / VIDEO
# ============================================================

OUTPUT = Path("output")
SCENES = OUTPUT / "video_scenes"
DEITIES = OUTPUT / "deity_images"

SCRIPT = OUTPUT / "daily_script.md"
VOICE = OUTPUT / "daily_voice.mp3"
VIDEO = OUTPUT / "daily_video.mp4"
CREDITS = OUTPUT / "deity_credits.txt"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
VOICE_NAME = "hi-IN-SwaraNeural"

FONT_URL = (
    "https://github.com/googlefonts/"
    "noto-fonts/raw/main/hinted/ttf/"
    "NotoSansDevanagari/"
    "NotoSansDevanagari-Regular.ttf"
)
FONT_PATH = OUTPUT / "NotoSansDevanagari-Regular.ttf"


# ============================================================
# RASHI -> DEVOTIONAL ASSOCIATION
#
# Direct upload.wikimedia.org URLs are used.
# If any external image fails, the video continues with a
# locally generated devotional fallback rather than failing.
# ============================================================

RASHIS = [
    {
        "name": "मेष",
        "emoji": "♈",
        "deity": "हनुमान जी",
        "image": "hanuman.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b4/Hanuman%201.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Hanuman_1.jpg",
        "license": "CC BY-SA 4.0",
    },
    {
        "name": "वृषभ",
        "emoji": "♉",
        "deity": "महालक्ष्मी जी",
        "image": "lakshmi.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/dd/Shreelaxmi.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shreelaxmi.jpg",
        "license": "Wikimedia Commons - see source",
    },
    {
        "name": "मिथुन",
        "emoji": "♊",
        "deity": "श्री गणेश जी",
        "image": "ganesh.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/9/93/Ganesh%20with%20Garland.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Ganesh_with_Garland.jpg",
        "license": "Wikimedia Commons - see source",
    },
    {
        "name": "कर्क",
        "emoji": "♋",
        "deity": "भगवान शिव",
        "image": "shiva.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/5/59/Shiv%207.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shiv_7.jpg",
        "license": "Wikimedia Commons - see source",
    },
    {
        "name": "सिंह",
        "emoji": "♌",
        "deity": "सूर्य देव",
        "image": "surya.webp",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/f/f6/"
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
        "url": "https://upload.wikimedia.org/wikipedia/commons/9/93/Ganesh%20with%20Garland.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Ganesh_with_Garland.jpg",
        "license": "Wikimedia Commons - see source",
    },
    {
        "name": "तुला",
        "emoji": "♎",
        "deity": "महालक्ष्मी जी",
        "image": "lakshmi.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/dd/Shreelaxmi.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shreelaxmi.jpg",
        "license": "Wikimedia Commons - see source",
    },
    {
        "name": "वृश्चिक",
        "emoji": "♏",
        "deity": "हनुमान जी",
        "image": "hanuman.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b4/Hanuman%201.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Hanuman_1.jpg",
        "license": "CC BY-SA 4.0",
    },
    {
        "name": "धनु",
        "emoji": "♐",
        "deity": "भगवान विष्णु",
        "image": "vishnu.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/e/e7/"
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
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/4a/Shani.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shani.jpg",
        "license": "Public Domain",
    },
    {
        "name": "कुंभ",
        "emoji": "♒",
        "deity": "शनि देव",
        "image": "shani.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/4a/Shani.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shani.jpg",
        "license": "Public Domain",
    },
    {
        "name": "मीन",
        "emoji": "♓",
        "deity": "भगवान विष्णु",
        "image": "vishnu.jpg",
        "url": (
            "https://upload.wikimedia.org/wikipedia/commons/e/e7/"
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
# BASIC HELPERS
# ============================================================

def run(command, timeout=600):
    print("RUN:", " ".join(str(x) for x in command))
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )


def get_font(size):
    OUTPUT.mkdir(parents=True, exist_ok=True)

    if not FONT_PATH.exists():
        request = urllib.request.Request(
            FONT_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 Chrome/124 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            FONT_PATH.write_bytes(response.read())

    return ImageFont.truetype(str(FONT_PATH), size)


def wrap_text(text, width=28):
    lines = []
    for paragraph in text.splitlines():
        paragraph = paragraph.strip()
        if paragraph:
            lines.extend(textwrap.wrap(paragraph, width=width))
    return lines


# ============================================================
# SCRIPT
# ============================================================

def read_script():
    if not SCRIPT.exists():
        raise RuntimeError("output/daily_script.md was not generated.")

    text = SCRIPT.read_text(encoding="utf-8").strip()

    if not text:
        raise RuntimeError("daily_script.md is empty.")

    return text


def find_rashi_sections(script):
    sections = {}

    for rashi in RASHIS:
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
            position = script.find(pattern)
            if position >= 0:
                start = position
                break

        if start < 0:
            continue

        end = len(script)

        for other in RASHIS:
            if other["name"] == name:
                continue

            for pattern in [
                f"{other['name']} राशि",
                f"राशि: {other['name']}",
                f"**{other['name']}**",
                f"### {other['name']}",
                f"## {other['name']}",
            ]:
                position = script.find(
                    pattern,
                    start + len(name) + 2,
                )
                if 0 <= position < end:
                    end = position

        section = script[start:end].strip()
        if section:
            sections[name] = section

    return sections


def fallback_section(rashi, script):
    matches = []
    for line in script.splitlines():
        if rashi["name"] in line:
            line = line.strip()
            if line:
                matches.append(line)

    if matches:
        return "\n".join(matches[:8])

    return (
        f"{rashi['name']} राशि के लिए आज के ग्रह गोचर "
        "के सामान्य संकेत।"
    )


# ============================================================
# DEITY ART
# ============================================================

def download_file(url, destination, retries=3):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 Chrome/124 Safari/537.36"
        ),
        "Accept": (
            "image/avif,image/webp,image/apng,image/svg+xml,"
            "image/*,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(1, retries + 1):
        try:
            print(
                f"Downloading deity artwork "
                f"(attempt {attempt}/{retries})"
            )

            request = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()

            if not data:
                raise RuntimeError("Downloaded file is empty.")

            destination.write_bytes(data)

            with Image.open(destination) as test_image:
                test_image.verify()

            print(f"Artwork ready: {destination}")
            return True

        except Exception as error:
            print(f"Artwork download failed: {error}")

            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass

            if attempt < retries:
                time.sleep(attempt * 2)

    return False


def create_deity_fallback(deity, destination):
    """
    Guaranteed local fallback. It is deliberately devotional and visually
    prominent, so a remote image failure never breaks the video.
    """

    image = Image.new("RGB", (1000, 1250), (12, 5, 32))
    draw = ImageDraw.Draw(image)

    om_font = get_font(190)
    title_font = get_font(76)
    subtitle_font = get_font(42)

    # Large sacred Om.
    bbox = draw.textbbox((0, 0), "ॐ", font=om_font)
    draw.text(
        ((1000 - (bbox[2] - bbox[0])) / 2, 180),
        "ॐ",
        font=om_font,
        fill=(255, 215, 80),
    )

    bbox = draw.textbbox((0, 0), deity, font=title_font)
    draw.text(
        ((1000 - (bbox[2] - bbox[0])) / 2, 560),
        deity,
        font=title_font,
        fill=(255, 255, 255),
    )

    subtitle = "दिव्य शक्ति • शुभ ऊर्जा • आशीर्वाद"
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(
        ((1000 - (bbox[2] - bbox[0])) / 2, 710),
        subtitle,
        font=subtitle_font,
        fill=(255, 220, 130),
    )

    image.save(destination, quality=95)


def download_deity_images():
    DEITIES.mkdir(parents=True, exist_ok=True)

    unique = {}
    for item in RASHIS:
        unique[item["image"]] = item

    credit_lines = [
        "DEVOTIONAL ARTWORK CREDITS",
        "===========================",
        "",
    ]

    for filename, item in unique.items():
        destination = DEITIES / filename

        if not destination.exists():
            ok = download_file(
                item["url"],
                destination,
                retries=3,
            )

            if not ok:
                print(
                    f"Using local devotional fallback for "
                    f"{item['deity']}"
                )
                create_deity_fallback(
                    item["deity"],
                    destination,
                )

                credit_lines.extend([
                    f"{item['deity']}",
                    "Fallback devotional artwork generated locally.",
                    "",
                ])
                continue

        credit_lines.extend([
            f"{item['deity']}",
            f"Source: {item['source']}",
            f"License: {item['license']}",
            f"Image URL: {item['url']}",
            "",
        ])

    CREDITS.write_text(
        "\n".join(credit_lines),
        encoding="utf-8",
    )


# ============================================================
# IMAGE COMPOSITION
# ============================================================

def fit_crop(image, target_w, target_h):
    """
    Fill a target rectangle while preserving aspect ratio.
    """
    image = image.convert("RGB")

    scale = max(
        target_w / image.width,
        target_h / image.height,
    )

    new_w = max(1, int(image.width * scale))
    new_h = max(1, int(image.height * scale))

    image = image.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS,
    )

    left = max(0, (new_w - target_w) // 2)
    top = max(0, (new_h - target_h) // 2)

    return image.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h,
        )
    )


def create_intro():
    path = SCENES / "000_intro.jpg"

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (10, 5, 28),
    )
    draw = ImageDraw.Draw(image)

    om_font = get_font(160)
    title_font = get_font(78)
    subtitle_font = get_font(48)
    small_font = get_font(34)

    bbox = draw.textbbox((0, 0), "ॐ", font=om_font)
    draw.text(
        ((WIDTH - bbox[2] + bbox[0]) / 2, 300),
        "ॐ",
        font=om_font,
        fill=(255, 215, 80),
    )

    title = "दैनिक वैदिक ज्योतिष"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(
        ((WIDTH - (bbox[2] - bbox[0])) / 2, 600),
        title,
        font=title_font,
        fill=(255, 255, 255),
    )

    subtitle = "आज का गोचर विश्लेषण"
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(
        ((WIDTH - (bbox[2] - bbox[0])) / 2, 750),
        subtitle,
        font=subtitle_font,
        fill=(255, 220, 130),
    )

    footer = "निरयन • लाहिरी • चंद्र राशि"
    bbox = draw.textbbox((0, 0), footer, font=small_font)
    draw.text(
        ((WIDTH - (bbox[2] - bbox[0])) / 2, 1500),
        footer,
        font=small_font,
        fill=(220, 215, 235),
    )

    image.save(path, quality=95)
    return path


def create_rashi_scene(rashi, content, output_path):
    """
    NEW PROMINENT-DEITY LAYOUT

    Vertical 1080x1920 composition:

      0-180       Rashi title
      220-1050    LARGE deity hero image (~830 px high)
      1050-1140   deity name
      1180-1690   astrology text
      1780-1840   footer

    The deity is intentionally much larger than in the previous version.
    """

    image_path = DEITIES / rashi["image"]

    deity = Image.open(image_path).convert("RGB")

    # --------------------------------------------------------
    # Background: enlarged, blurred version of the deity.
    # This gives the scene a devotional visual identity without
    # reducing the clarity of the foreground deity.
    # --------------------------------------------------------

    bg = fit_crop(
        deity,
        WIDTH,
        HEIGHT,
    )
    bg = bg.filter(
        ImageFilter.GaussianBlur(radius=28)
    )

    dark_overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 155),
    )

    canvas = Image.alpha_composite(
        bg.convert("RGBA"),
        dark_overlay,
    )

    draw = ImageDraw.Draw(canvas)

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    title_font = get_font(72)
    deity_font = get_font(48)
    body_font = get_font(37)
    footer_font = get_font(29)

    # --------------------------------------------------------
    # Rashi title
    # --------------------------------------------------------

    title = f"{rashi['emoji']} {rashi['name']} राशि"

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font,
    )

    draw.rounded_rectangle(
        (35, 35, WIDTH - 35, 175),
        radius=35,
        fill=(5, 2, 20, 215),
        outline=(255, 215, 80, 220),
        width=3,
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            62,
        ),
        title,
        font=title_font,
        fill=(255, 220, 90),
    )

    # --------------------------------------------------------
    # LARGE DEITY HERO PANEL
    # --------------------------------------------------------

    panel_x1 = 35
    panel_y1 = 215
    panel_x2 = WIDTH - 35
    panel_y2 = 1090

    draw.rounded_rectangle(
        (panel_x1, panel_y1, panel_x2, panel_y2),
        radius=42,
        fill=(2, 1, 15, 235),
        outline=(255, 215, 80, 240),
        width=5,
    )

    # Image area: approximately 820 x 760.
    target_w = 840
    target_h = 760

    deity_display = fit_crop(
        deity,
        target_w,
        target_h,
    )

    # Rounded-mask effect.
    mask = Image.new(
        "L",
        (target_w, target_h),
        0,
    )
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        (0, 0, target_w, target_h),
        radius=35,
        fill=255,
    )

    x = (WIDTH - target_w) // 2
    y = panel_y1 + 35

    canvas.paste(
        deity_display,
        (x, y),
        mask,
    )

    # Subtle border around hero image.
    draw.rounded_rectangle(
        (
            x,
            y,
            x + target_w,
            y + target_h,
        ),
        radius=35,
        outline=(255, 225, 130, 230),
        width=4,
    )

    # --------------------------------------------------------
    # DEITY NAME: PROMINENT
    # --------------------------------------------------------

    deity_label = f"॥ {rashi['deity']} ॥"

    bbox = draw.textbbox(
        (0, 0),
        deity_label,
        font=deity_font,
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            1000,
        ),
        deity_label,
        font=deity_font,
        fill=(255, 242, 200),
    )

    # --------------------------------------------------------
    # ASTROLOGY TEXT PANEL
    # --------------------------------------------------------

    text_top = 1140
    text_bottom = 1690

    draw.rounded_rectangle(
        (
            42,
            text_top,
            WIDTH - 42,
            text_bottom,
        ),
        radius=32,
        fill=(3, 2, 16, 235),
        outline=(160, 145, 190, 120),
        width=2,
    )

    lines = wrap_text(
        content,
        width=30,
    )

    y = text_top + 38

    for line in lines[:11]:
        draw.text(
            (75, y),
            line,
            font=body_font,
            fill=(255, 255, 255),
        )

        y += 51

        if y > text_bottom - 55:
            break

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    footer = "वैदिक गोचर • निरयन • लाहिरी"

    bbox = draw.textbbox(
        (0, 0),
        footer,
        font=footer_font,
    )

    draw.text(
        (
            (WIDTH - (bbox[2] - bbox[0])) / 2,
            1785,
        ),
        footer,
        font=footer_font,
        fill=(225, 220, 240),
    )

    canvas.convert("RGB").save(
        output_path,
        quality=95,
    )


def create_final():
    path = SCENES / "999_final.jpg"

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (10, 5, 28),
    )
    draw = ImageDraw.Draw(image)

    title_font = get_font(78)
    body_font = get_font(46)
    small_font = get_font(32)

    title = "🙏 धन्यवाद"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(
        ((WIDTH - (bbox[2] - bbox[0])) / 2, 400),
        title,
        font=title_font,
        fill=(255, 215, 80),
    )

    messages = [
        "दैनिक वैदिक ज्योतिष अपडेट",
        "वीडियो पसंद आए तो लाइक करें",
        "चैनल को सब्सक्राइब करें",
    ]

    y = 650
    for message in messages:
        bbox = draw.textbbox((0, 0), message, font=body_font)
        draw.text(
            ((WIDTH - (bbox[2] - bbox[0])) / 2, y),
            message,
            font=body_font,
            fill=(255, 255, 255),
        )
        y += 115

    disclaimer = (
        "यह प्रस्तुति पारंपरिक वैदिक ज्योतिषीय "
        "गोचर सिद्धांतों पर आधारित सामान्य जानकारी है।"
    )

    y = 1250
    for line in textwrap.wrap(disclaimer, width=35):
        bbox = draw.textbbox((0, 0), line, font=small_font)
        draw.text(
            ((WIDTH - (bbox[2] - bbox[0])) / 2, y),
            line,
            font=small_font,
            fill=(210, 205, 225),
        )
        y += 55

    image.save(path, quality=95)
    return path


# ============================================================
# VOICE
# ============================================================

async def create_voice(text):
    print("Generating Hindi narration...")

    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+5%",
        volume="+0%",
    )

    await communicate.save(str(VOICE))

    if not VOICE.exists():
        raise RuntimeError("Hindi voice was not created.")


def get_audio_duration(ffmpeg):
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

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


# ============================================================
# VIDEO BUILD
# ============================================================

def build_video(ffmpeg, scene_files, duration):
    print("Building final vertical video...")

    intro_duration = min(8.0, duration * 0.03)
    final_duration = min(8.0, duration * 0.03)

    rashi_files = scene_files[1:-1]

    remaining = duration - intro_duration - final_duration

    if remaining <= 0:
        raise RuntimeError("Invalid narration duration.")

    rashi_duration = remaining / max(1, len(rashi_files))

    concat_file = SCENES / "video_concat.txt"

    with concat_file.open("w", encoding="utf-8") as f:
        def add_scene(path, seconds):
            safe = str(path.resolve()).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
            f.write(f"duration {seconds:.3f}\n")

        add_scene(scene_files[0], intro_duration)

        for scene in rashi_files:
            add_scene(scene, rashi_duration)

        add_scene(scene_files[-1], final_duration)

        # concat demuxer needs the final file repeated.
        safe = str(scene_files[-1].resolve()).replace("'", "'\\''")
        f.write(f"file '{safe}'\n")

    silent_video = SCENES / "silent_video.mp4"

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
        f"scale={WIDTH}:{HEIGHT}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
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
        str(silent_video),
    ])

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
        str(VIDEO),
    ])

    if not VIDEO.exists():
        raise RuntimeError(
            "daily_video.mp4 was not created."
        )


# ============================================================
# MAIN
# ============================================================

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SCENES.mkdir(parents=True, exist_ok=True)
    DEITIES.mkdir(parents=True, exist_ok=True)

    # Clean only generated scene files.
    for pattern in (
        "*.jpg",
        "*.mp4",
        "video_concat.txt",
    ):
        for file in SCENES.glob(pattern):
            try:
                file.unlink()
            except Exception:
                pass

    script = read_script()

    print("Astrology script loaded.")

    # Deity preparation is isolated from astrology logic.
    download_deity_images()

    asyncio.run(create_voice(script))

    scene_files = []
    scene_files.append(create_intro())

    sections = find_rashi_sections(script)

    print(
        f"Detected {len(sections)} explicit Rashi sections."
    )

    # Always render all 12 Rashis.
    for index, rashi in enumerate(RASHIS, start=1):
        content = sections.get(rashi["name"])

        if not content:
            content = fallback_section(rashi, script)

        scene_path = (
            SCENES /
            f"{index:03d}_{rashi['name']}.jpg"
        )

        print(
            f"Rendering {index}/12: "
            f"{rashi['name']} -> {rashi['deity']}"
        )

        create_rashi_scene(
            rashi,
            content,
            scene_path,
        )

        scene_files.append(scene_path)

    scene_files.append(create_final())

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    duration = get_audio_duration(ffmpeg)

    print(
        f"Narration duration: {duration:.2f} seconds"
    )

    build_video(
        ffmpeg,
        scene_files,
        duration,
    )

    print()
    print("==========================================")
    print("VEDIC ASTROLOGY VIDEO COMPLETE")
    print("==========================================")
    print(f"VIDEO   : {VIDEO}")
    print(f"VOICE   : {VOICE}")
    print(f"CREDITS : {CREDITS}")
    print("==========================================")


if __name__ == "__main__":
    main()
