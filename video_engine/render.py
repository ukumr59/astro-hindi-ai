"""
DAILY VEDIC ASTROLOGY VIDEO ENGINE

Input:
    output/daily_script.md

Output:
    output/daily_video.mp4
    output/daily_voice.mp3
    output/deity_credits.txt

Video:
    1080 x 1920
    Vertical / YouTube Shorts compatible
    Hindi narration
    Rashi-by-Rashi devotional visuals
    Deity prominently displayed
"""

from pathlib import Path
import asyncio
import subprocess
import textwrap
import urllib.request
import re
import shutil

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
# VIDEO SETTINGS
# ============================================================

WIDTH = 1080
HEIGHT = 1920
FPS = 30

VOICE_NAME = "hi-IN-SwaraNeural"


# ============================================================
# RASHI / DEITY CONFIGURATION
# ============================================================

RASHIS = [
    {
        "name": "मेष",
        "emoji": "♈",
        "deity": "हनुमान जी",
        "file": "Hanuman 1.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Hanuman_1.jpg",
        "license": "CC BY-SA 4.0",
    },
    {
        "name": "वृषभ",
        "emoji": "♉",
        "deity": "महालक्ष्मी जी",
        "file": "Shreelaxmi.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shreelaxmi.jpg",
        "license": "Wikimedia Commons - verify file license before publication",
    },
    {
        "name": "मिथुन",
        "emoji": "♊",
        "deity": "श्री गणेश जी",
        "file": "Ganesh with Garland.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Ganesh_with_Garland.jpg",
        "license": "Wikimedia Commons - verify file license before publication",
    },
    {
        "name": "कर्क",
        "emoji": "♋",
        "deity": "भगवान शिव",
        "file": "Shiv 7.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shiv_7.jpg",
        "license": "Wikimedia Commons - verify file license before publication",
    },
    {
        "name": "सिंह",
        "emoji": "♌",
        "deity": "सूर्य देव",
        "file": "सूर्य देव मूर्ति (Sun God Idol).webp",
        "source": "https://commons.wikimedia.org/wiki/File:%E0%A4%B8%E0%A5%82%E0%A4%B0%E0%A5%8D%E0%A4%AF_%E0%A4%A6%E0%A5%87%E0%A4%B5_%E0%A4%AE%E0%A5%82%E0%A4%B0%E0%A5%8D%E0%A4%A4%E0%A4%BF_(Sun_God_Idol).webp",
        "license": "Wikimedia Commons - verify file license before publication",
    },
    {
        "name": "कन्या",
        "emoji": "♍",
        "deity": "श्री गणेश जी",
        "file": "Ganesh with Garland.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Ganesh_with_Garland.jpg",
        "license": "Wikimedia Commons - verify file license before publication",
    },
    {
        "name": "तुला",
        "emoji": "♎",
        "deity": "महालक्ष्मी जी",
        "file": "Shreelaxmi.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shreelaxmi.jpg",
        "license": "Wikimedia Commons - verify file license before publication",
    },
    {
        "name": "वृश्चिक",
        "emoji": "♏",
        "deity": "हनुमान जी",
        "file": "Hanuman 1.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Hanuman_1.jpg",
        "license": "CC BY-SA 4.0",
    },
    {
        "name": "धनु",
        "emoji": "♐",
        "deity": "भगवान विष्णु",
        "file": "Hand-drawn image of Vishnu, Mogao Caves.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Hand-drawn_image_of_Vishnu,_Mogao_Caves.jpg",
        "license": "Wikimedia Commons - verify file license before publication",
    },
    {
        "name": "मकर",
        "emoji": "♑",
        "deity": "शनि देव",
        "file": "Shani.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shani.jpg",
        "license": "Public domain",
    },
    {
        "name": "कुंभ",
        "emoji": "♒",
        "deity": "शनि देव",
        "file": "Shani.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Shani.jpg",
        "license": "Public domain",
    },
    {
        "name": "मीन",
        "emoji": "♓",
        "deity": "भगवान विष्णु",
        "file": "Hand-drawn image of Vishnu, Mogao Caves.jpg",
        "source": "https://commons.wikimedia.org/wiki/File:Hand-drawn_image_of_Vishnu,_Mogao_Caves.jpg",
        "license": "Wikimedia Commons - verify file license before publication",
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
# UTILITIES
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
        timeout=timeout,
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {result.returncode}"
        )


def get_font(size):

    if not FONT_PATH.exists():

        print(
            "Downloading Devanagari font..."
        )

        urllib.request.urlretrieve(
            FONT_URL,
            FONT_PATH
        )

    return ImageFont.truetype(
        str(FONT_PATH),
        size
    )


def wrap_text(text, width=25):

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
# SCRIPT
# ============================================================

def read_script():

    if not SCRIPT.exists():

        raise RuntimeError(
            "daily_script.md not found."
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
# DOWNLOAD DEITY ART
# ============================================================

def download_deity_images():

    DEITIES.mkdir(
        parents=True,
        exist_ok=True
    )

    unique = {}

    for item in RASHIS:

        unique[
            item["file"]
        ] = item

    for filename, item in unique.items():

        destination = (
            DEITIES / filename
        )

        if destination.exists():

            print(
                f"Already downloaded: {filename}"
            )

            continue

        print(
            f"Downloading deity artwork: "
            f"{item['deity']}"
        )

        encoded = urllib.parse.quote(
            filename,
            safe=""
        )

        url = (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/"
            f"{encoded}"
        )

        urllib.request.urlretrieve(
            url,
            destination
        )

    # Record credits.
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

        for item in unique.values():

            f.write(
                f"{item['deity']}\n"
            )

            f.write(
                f"File: {item['file']}\n"
            )

            f.write(
                f"Source: {item['source']}\n"
            )

            f.write(
                f"License: {item['license']}\n\n"
            )


# ============================================================
# RASHI SECTION EXTRACTION
# ============================================================

def find_rashi_sections(script):

    sections = {}

    for index, rashi in enumerate(
        RASHIS
    ):

        name = rashi["name"]

        start_patterns = [
            f"{name} राशि",
            f"राशि: {name}",
            f"**{name}**",
            f"### {name}",
            f"## {name}",
        ]

        start = -1

        for pattern in start_patterns:

            found = script.find(
                pattern
            )

            if found >= 0:

                start = found
                break

        if start < 0:
            continue

        end = len(script)

        for next_rashi in RASHIS:

            if next_rashi["name"] == name:
                continue

            for pattern in [
                f"{next_rashi['name']} राशि",
                f"राशि: {next_rashi['name']}",
                f"**{next_rashi['name']}**",
                f"### {next_rashi['name']}",
                f"## {next_rashi['name']}",
            ]:

                found = script.find(
                    pattern,
                    start + len(name) + 2
                )

                if found >= 0 and found < end:
                    end = found

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

    # Find references to the Rashi anywhere
    # in the generated script.
    name = rashi["name"]

    matches = []

    for line in script.splitlines():

        if name in line:

            line = line.strip()

            if line:

                matches.append(
                    line
                )

    if matches:

        return "\n".join(
            matches[:8]
        )

    return (
        f"{name} राशि के लिए आज के "
        "गोचर संकेतों का विश्लेषण प्रस्तुत है।"
    )


# ============================================================
# SCENE IMAGE
# ============================================================

def create_rashi_scene(
    rashi,
    content,
    output_path
):

    image_path = (
        DEITIES
        / rashi["file"]
    )

    if not image_path.exists():

        raise RuntimeError(
            f"Missing deity image: {image_path}"
        )

    deity = Image.open(
        image_path
    ).convert("RGB")

    # --------------------------------------------------------
    # Background
    # --------------------------------------------------------

    background = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (13, 7, 31)
    )

    # Large blurred deity background.
    bg = deity.copy()

    bg.thumbnail(
        (WIDTH, HEIGHT)
    )

    background.paste(
        bg,
        (
            (WIDTH - bg.width) // 2,
            (HEIGHT - bg.height) // 2
        )
    )

    background = background.filter(
        ImageFilter.GaussianBlur(
            radius=18
        )
    )

    # Dark overlay.
    overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 145)
    )

    background = Image.alpha_composite(
        background.convert("RGBA"),
        overlay
    ).convert("RGB")

    draw = ImageDraw.Draw(
        background
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    title_font = get_font(
        72
    )

    deity_font = get_font(
        48
    )

    body_font = get_font(
        40
    )

    footer_font = get_font(
        30
    )

    title = (
        f"{rashi['emoji']}  "
        f"{rashi['name']} राशि"
    )

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    title_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (WIDTH - title_width) / 2,
            90
        ),
        title,
        font=title_font,
        fill=(255, 215, 80)
    )

    # --------------------------------------------------------
    # Deity panel
    # --------------------------------------------------------

    panel_top = 250
    panel_bottom = 920

    draw.rounded_rectangle(
        (
            45,
            panel_top,
            WIDTH - 45,
            panel_bottom
        ),
        radius=35,
        fill=(5, 3, 18, 210),
        outline=(255, 215, 80),
        width=3
    )

    # Fit deity prominently.
    deity = Image.open(
        image_path
    ).convert("RGB")

    max_w = 600
    max_h = 600

    deity.thumbnail(
        (
            max_w,
            max_h
        )
    )

    x = (
        WIDTH - deity.width
    ) // 2

    y = (
        panel_top
        + 35
        + (
            max_h - deity.height
        ) // 2
    )

    background.paste(
        deity,
        (
            x,
            y
        )
    )

    deity_text = (
        f"शुभ आराध्य: {rashi['deity']}"
    )

    bbox = draw.textbbox(
        (0, 0),
        deity_text,
        font=deity_font
    )

    deity_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (WIDTH - deity_width) / 2,
            850
        ),
        deity_text,
        font=deity_font,
        fill=(255, 245, 210)
    )

    # --------------------------------------------------------
    # Astrology text
    # --------------------------------------------------------

    content_top = 990

    draw.rounded_rectangle(
        (
            55,
            content_top,
            WIDTH - 55,
            1660
        ),
        radius=30,
        fill=(5, 3, 18, 225)
    )

    lines = wrap_text(
        content,
        width=29
    )

    y = content_top + 55

    for line in lines[:13]:

        draw.text(
            (
                90,
                y
            ),
            line,
            font=body_font,
            fill=(255, 255, 255)
        )

        y += 62

        if y > 1580:
            break

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    footer = (
        "निरयन • लाहिरी • चंद्र राशि आधारित गोचर"
    )

    bbox = draw.textbbox(
        (0, 0),
        footer,
        font=footer_font
    )

    footer_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (WIDTH - footer_width) / 2,
            1780
        ),
        footer,
        font=footer_font,
        fill=(220, 215, 235)
    )

    background.save(
        output_path,
        quality=95
    )


# ============================================================
# INTRO SCENE
# ============================================================

def create_intro():

    path = (
        SCENES
        / "000_intro.jpg"
    )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (10, 5, 25)
    )

    draw = ImageDraw.Draw(
        image
    )

    title_font = get_font(
        78
    )

    subtitle_font = get_font(
        46
    )

    small_font = get_font(
        34
    )

    lines = [
        "ॐ",
        "दैनिक वैदिक ज्योतिष",
        "आज का गोचर विश्लेषण",
    ]

    y = 430

    for index, text in enumerate(
        lines
    ):

        font = (
            title_font
            if index < 2
            else subtitle_font
        )

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font
        )

        width = (
            bbox[2] - bbox[0]
        )

        draw.text(
            (
                (WIDTH - width) / 2,
                y
            ),
            text,
            font=font,
            fill=(
                255,
                215,
                80
            )
            if index == 0
            else (
                255,
                255,
                255
            )
        )

        y += 150

    footer = (
        "निरयन • लाहिरी • चंद्र राशि"
    )

    bbox = draw.textbbox(
        (0, 0),
        footer,
        font=small_font
    )

    width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (WIDTH - width) / 2,
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
# FINAL SCENE
# ============================================================

def create_final():

    path = (
        SCENES
        / "999_final.jpg"
    )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (10, 5, 25)
    )

    draw = ImageDraw.Draw(
        image
    )

    title_font = get_font(
        70
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

    width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (WIDTH - width) / 2,
            450
        ),
        title,
        font=title_font,
        fill=(255, 215, 80)
    )

    messages = [
        "दैनिक वैदिक ज्योतिष अपडेट",
        "पसंद आए तो वीडियो को लाइक करें",
        "और चैनल को सब्सक्राइब करें",
    ]

    y = 650

    for message in messages:

        bbox = draw.textbbox(
            (0, 0),
            message,
            font=body_font
        )

        width = (
            bbox[2] - bbox[0]
        )

        draw.text(
            (
                (WIDTH - width) / 2,
                y
            ),
            message,
            font=body_font,
            fill=(255, 255, 255)
        )

        y += 110

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

        width = (
            bbox[2] - bbox[0]
        )

        draw.text(
            (
                (WIDTH - width) / 2,
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
# CREATE AUDIO
# ============================================================

async def create_voice(text):

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
            "Voice file was not created."
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
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
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

    # --------------------------------------------------------
    # Calculate scene durations.
    #
    # Intro = 5%
    # Final = 5%
    # Rashis share remaining time based on script length.
    # --------------------------------------------------------

    rashi_files = [
        path
        for path in scene_files
        if "intro" not in path.name
        and "final" not in path.name
    ]

    intro = [
        path
        for path in scene_files
        if "intro" in path.name
    ][0]

    final = [
        path
        for path in scene_files
        if "final" in path.name
    ][0]

    intro_duration = min(
        12.0,
        duration * 0.03
    )

    final_duration = min(
        12.0,
        duration * 0.03
    )

    available = (
        duration
        - intro_duration
        - final_duration
    )

    if available <= 0:

        raise RuntimeError(
            "Video duration is too short."
        )

    each = (
        available
        / max(
            1,
            len(rashi_files)
        )
    )

    # --------------------------------------------------------
    # Create concat file.
    # --------------------------------------------------------

    concat_file = (
        SCENES
        / "video_concat.txt"
    )

    with concat_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        def add_scene(
            path,
            seconds
        ):

            resolved = str(
                path.resolve()
            ).replace(
                "'",
                "'\\''"
            )

            f.write(
                f"file '{resolved}'\n"
            )

            f.write(
                f"duration {seconds:.3f}\n"
            )

        add_scene(
            intro,
            intro_duration
        )

        for scene in rashi_files:

            add_scene(
                scene,
                each
            )

        add_scene(
            final,
            final_duration
        )

        # concat demuxer requires final file
        # repeated to preserve final duration.
        resolved = str(
            final.resolve()
        ).replace(
            "'",
            "'\\''"
        )

        f.write(
            f"file '{resolved}'\n"
        )

    silent_video = (
        SCENES
        / "silent_video.mp4"
    )

    # --------------------------------------------------------
    # Render slideshow.
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
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2"
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
    # Add narration.
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
            "Final video was not created."
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
    # Read astrology script.
    # --------------------------------------------------------

    script = read_script()

    # --------------------------------------------------------
    # Download devotional artwork.
    # --------------------------------------------------------

    download_deity_images()

    # --------------------------------------------------------
    # Generate Hindi voice.
    # --------------------------------------------------------

    asyncio.run(
        create_voice(
            script
        )
    )

    # --------------------------------------------------------
    # Create intro.
    # --------------------------------------------------------

    scene_files = []

    intro = create_intro()

    scene_files.append(
        intro
    )

    # --------------------------------------------------------
    # Find Rashi sections.
    # --------------------------------------------------------

    sections = find_rashi_sections(
        script
    )

    print(
        f"Detected {len(sections)} Rashi sections."
    )

    # --------------------------------------------------------
    # Create 12 Rashi scenes.
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
            SCENES
            / f"{index:03d}_{rashi['name']}.jpg"
        )

        print(
            f"Creating scene "
            f"{index}/12: "
            f"{rashi['name']} "
            f"→ {rashi['deity']}"
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
    # Final scene.
    # --------------------------------------------------------

    final = create_final()

    scene_files.append(
        final
    )

    # --------------------------------------------------------
    # Get bundled FFmpeg.
    # --------------------------------------------------------

    ffmpeg = (
        imageio_ffmpeg.get_ffmpeg_exe()
    )

    print(
        f"Bundled FFmpeg: {ffmpeg}"
    )

    # --------------------------------------------------------
    # Build final MP4.
    # --------------------------------------------------------

    duration = get_audio_duration(
        ffmpeg
    )

    print(
        f"Narration duration: "
        f"{duration:.1f} seconds"
    )

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
        f"Video:   {VIDEO}"
    )
    print(
        f"Voice:   {VOICE}"
    )
    print(
        f"Credits: {CREDITS}"
    )
    print(
        f"Scenes:  {SCENES}"
    )
    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()
