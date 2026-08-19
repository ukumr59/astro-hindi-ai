"""
Daily Astro Hindi Video Renderer - V4

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


def download_deity(item_index, deity, query):
    destination = DEITIES / f"deity_{item_index:02d}.jpg"

    # Reuse a previously downloaded real image.
    if destination.exists():
        try:
            with Image.open(destination) as img:
                if img.width > 300 and img.height > 300:
                    return destination, "cached", ""
        except Exception:
            try:
                destination.unlink()
            except Exception:
                pass

    search_queries = [
        query,
        f"{deity} Hindu deity",
        f"{deity} temple",
    ]

    last_error = None

    for search_query in search_queries:
        try:
            result = commons_search(search_query)

            if not result:
                continue

            print(
                f"Resolved {deity}: "
                f"{result['title']}"
            )

            data = request_bytes(result["url"])

            temp = destination.with_suffix(".download")
            temp.write_bytes(data)

            with Image.open(temp) as img:
                img.verify()

            # Reopen and normalize to JPEG.
            with Image.open(temp) as img:
                normalized = img.convert("RGB")
                normalized.save(
                    destination,
                    "JPEG",
                    quality=95,
                )

            temp.unlink(missing_ok=True)

            return (
                destination,
                result["title"],
                result["url"],
            )

        except Exception as exc:
            last_error = exc
            print(
                f"Could not download {deity} "
                f"from Commons: {exc}"
            )

    raise RuntimeError(
        f"Could not obtain a real deity image for {deity}. "
        f"Last error: {last_error}"
    )


def prepare_deities():
    DEITIES.mkdir(
        parents=True,
        exist_ok=True,
    )

    credits = [
        "REAL DEITY ARTWORK",
        "==================",
        "",
    ]

    resolved = {}

    # Same deity gets the same downloaded image.
    unique = {}

    for _, _, deity, query in RASHIS:
        unique[deity] = query

    for number, (deity, query) in enumerate(
        unique.items(),
        start=1,
    ):
        path, title, source_url = download_deity(
            number,
            deity,
            query,
        )

        resolved[deity] = path

        credits.extend([
            deity,
            f"Commons file: {title}",
            f"Image URL: {source_url}",
            "",
        ])

    CREDITS.write_text(
        "\n".join(credits),
        encoding="utf-8",
    )

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
    deity_font = get_font(54)
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

    hero = crop_cover(
        deity_img,
        hero_w,
        hero_h,
    )

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
        hero,
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

    # Deity name.
    deity_text = f"🙏 {deity} 🙏"

    box = draw.textbbox(
        (0, 0),
        deity_text,
        font=deity_font,
    )

    draw.text(
        (
            (WIDTH - (box[2] - box[0])) / 2,
            1010,
        ),
        deity_text,
        font=deity_font,
        fill=(255, 242, 200),
    )

    # Astrology panel.
    text_panel = (
        42,
        1150,
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
    Converts one static poster into an animated clip.

    Animation:
    - slow zoom
    - slow horizontal drift
    - gentle brightness breathing

    IMPORTANT:
    The brightness expression intentionally uses `t`, not `on`.
    `on` belongs to zoompan; `t` belongs to the eq filter.
    """

    output = SCENES / f"clip_{index:02d}.mp4"

    frames = max(
        1,
        int(round(duration * FPS)),
    )

    zoom_expr = (
        "min(max(zoom,pzoom)+0.00020,1.14)"
    )

    # No embedded quotes: this is passed directly to subprocess,
    # not through a shell.
    filtergraph = (
        f"zoompan="
        f"z={zoom_expr}:"
        f"x='iw/2-(iw/zoom/2)+18*sin(on/180)':"
        f"y='ih/2-(ih/zoom/2)+12*cos(on/220)':"
        f"d={frames}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS},"
        f"eq=brightness=0.012*sin(2*PI*t/18):"
        f"contrast=1.025:saturation=1.06"
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
    # REAL DEITY IMAGE DOWNLOAD
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
    print("Deity art: Wikimedia Commons real artwork")
    print("========================================")


if __name__ == "__main__":
    main()

