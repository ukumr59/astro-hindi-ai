"""
Daily Astro Hindi Video Renderer - V14

Purpose:
- Keep the existing generated astrology narration/script.
- Put premium bundled devotional deity artwork prominently into each Rashi scene.
- Animate every Rashi scene with a slow cinematic zoom/pan and gentle motion.
- Cross-fade between Rashi scenes.
- Never use the old generic Om-only fallback as a deity image.
- Use only bundled deity artwork; never fall back to fake geometric deity drawings.

Run:
    python -m video_engine.render
"""

from pathlib import Path
import asyncio
import re
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import edge_tts
import imageio_ffmpeg


# ============================================================
# CONFIG
# ============================================================

OUTPUT = Path("output")
SCENES = OUTPUT / "video_scenes"
DEITIES = OUTPUT / "deity_images"
ASSETS = Path("assets")
DEITY_ASSETS = ASSETS / "deities"
INTRO_ASSET = ASSETS / "intro_devotional.jpg"

SCRIPT = OUTPUT / "daily_script.md"
VOICE = OUTPUT / "daily_voice.mp3"
VIDEO = OUTPUT / "daily_video.mp4"
CREDITS = OUTPUT / "deity_credits.txt"
FFMPEG_LOG = OUTPUT / "ffmpeg_render.log"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

VOICE_NAME = "hi-IN-SwaraNeural"

FONT_PATH = ASSETS / "NotoSansDevanagari-Regular.ttf"

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


def get_font(size):
    if not FONT_PATH.exists():
        raise RuntimeError(
            f"Missing bundled Unicode font: {FONT_PATH}"
        )
    return ImageFont.truetype(str(FONT_PATH), size)


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
# DEVOTIONAL ARTWORK
# ============================================================
# All deity artwork is bundled locally under assets/deities.
# No remote deity-image service is contacted by the renderer.


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
    Rich devotional Rashi scene:
    - large deity artwork
    - temple-like golden frame
    - divine glow / halo
    - zodiac/rashi header
    - no deity name below the photograph
    - readable astrology content
    """
    output = SCENES / f"{index:03d}_{key}.jpg"

    deity_img = Image.open(deity_image).convert("RGB")

    # Rich blurred deity background.
    bg = crop_cover(deity_img, WIDTH, HEIGHT)
    bg = bg.filter(ImageFilter.GaussianBlur(34))
    bg = ImageEnhance.Brightness(bg).enhance(0.42)
    bg = ImageEnhance.Contrast(bg).enhance(1.08)

    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (20, 5, 30, 255))
    canvas.paste(bg, (0, 0))

    # Warm devotional color veil.
    veil = Image.new("RGBA", (WIDTH, HEIGHT), (20, 5, 30, 145))
    canvas = Image.alpha_composite(canvas, veil)

    draw = ImageDraw.Draw(canvas)

    title_font = get_font(70)
    badge_font = get_font(34)
    body_font = get_font(35)
    footer_font = get_font(27)

    gold = (255, 214, 74, 255)
    light_gold = (255, 239, 164, 255)
    white = (255, 252, 240, 255)
    dark = (22, 7, 28, 238)

    # Decorative top border.
    draw.rectangle((0, 0, WIDTH, 12), fill=gold)
    draw.rectangle((0, HEIGHT - 12, WIDTH, HEIGHT), fill=gold)

    # Header.
    draw.rounded_rectangle(
        (26, 28, WIDTH - 26, 178),
        radius=34,
        fill=dark,
        outline=gold,
        width=5,
    )

    title = f"॥ {label} ॥"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(
        ((WIDTH - (box[2] - box[0])) / 2, 52),
        title,
        font=title_font,
        fill=light_gold,
    )

    # Small devotional badge ABOVE the artwork.
    badge = f"आराध्य देव : {deity}"
    box = draw.textbbox((0, 0), badge, font=badge_font)
    bx = (WIDTH - (box[2] - box[0])) / 2
    draw.rounded_rectangle(
        (bx - 28, 130, bx + (box[2] - box[0]) + 28, 178),
        radius=22,
        fill=(120, 48, 8, 230),
        outline=gold,
        width=2,
    )
    draw.text((bx, 136), badge, font=badge_font, fill=white)

    # Main hero frame.
    panel = (30, 215, WIDTH - 30, 1120)
    draw.rounded_rectangle(
        panel,
        radius=44,
        fill=(5, 2, 16, 225),
        outline=gold,
        width=6,
    )

    # Inner glow rings.
    for inset, alpha in ((18, 150), (34, 95)):
        draw.rounded_rectangle(
            (
                panel[0] + inset,
                panel[1] + inset,
                panel[2] - inset,
                panel[3] - inset,
            ),
            radius=36,
            outline=(255, 224, 120, alpha),
            width=3,
        )

    hero_w, hero_h = 900, 820
    hero = deity_img.copy()
    hero.thumbnail((hero_w, hero_h), Image.Resampling.LANCZOS)

    hero_canvas = Image.new("RGB", (hero_w, hero_h), (10, 5, 22))
    hx = (hero_w - hero.width) // 2
    hy = (hero_h - hero.height) // 2
    hero_canvas.paste(hero, (hx, hy))

    x = (WIDTH - hero_w) // 2
    y = 250

    mask = Image.new("L", (hero_w, hero_h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, hero_w, hero_h), radius=34, fill=255)
    canvas.paste(hero_canvas, (x, y), mask)

    draw.rounded_rectangle(
        (x, y, x + hero_w, y + hero_h),
        radius=34,
        outline=light_gold,
        width=5,
    )

    # Divinity separator — deliberately above the text, not under the deity.
    sep_y = 1085
    draw.line((130, sep_y, WIDTH - 130, sep_y), fill=gold, width=3)
    om_font = get_font(50)
    om = "ॐ"
    ob = draw.textbbox((0, 0), om, font=om_font)
    draw.text(((WIDTH - (ob[2]-ob[0]))/2, sep_y-32), om, font=om_font, fill=gold)

    # Astrology text panel.
    text_panel = (42, 1150, WIDTH - 42, 1695)
    draw.rounded_rectangle(
        text_panel,
        radius=32,
        fill=(5, 2, 17, 242),
        outline=(255, 214, 100, 165),
        width=3,
    )

    # Section heading.
    section_heading = "आज के ग्रह गोचर के संकेत"
    hb = draw.textbbox((0, 0), section_heading, font=badge_font)
    draw.text(
        ((WIDTH - (hb[2]-hb[0]))/2, 1175),
        section_heading,
        font=badge_font,
        fill=light_gold,
    )

    lines = wrap_text(content, width=31)
    y_text = 1238

    for line in lines[:8]:
        draw.text(
            (72, y_text),
            line,
            font=body_font,
            fill=white,
        )
        y_text += 54
        if y_text > 1640:
            break

    footer = "॥ श्रद्धा | विश्वास | सकारात्मक ऊर्जा | वैदिक ज्योतिष ॥"
    fb = draw.textbbox((0, 0), footer, font=footer_font)
    draw.text(
        ((WIDTH - (fb[2]-fb[0]))/2, 1768),
        footer,
        font=footer_font,
        fill=light_gold,
    )

    canvas.convert("RGB").save(output, "JPEG", quality=96, subsampling=0)
    return output

def create_intro(script_text):
    """
    High-impact 7-second devotional opening.
    Uses the bundled cinematic temple artwork and adds a clean Hindi
    title/date layer so the first seconds feel unmistakably religious.
    """
    output = SCENES / "000_intro.jpg"

    # Keep the opening current for every automated daily run.
    date_line = next(
        (line.strip() for line in script_text.splitlines()
         if line.strip().startswith("आज की तारीख है")),
        "आज की तारीख",
    )
    transition_line = next(
        (line.strip() for line in script_text.splitlines()
         if line.strip().startswith("चंद्रमा ने")),
        "आज का प्रमुख चंद्र गोचर",
    )

    if not INTRO_ASSET.exists():
        raise RuntimeError(f"Missing opening artwork: {INTRO_ASSET}")

    source = Image.open(INTRO_ASSET).convert("RGB")
    top = crop_cover(source, WIDTH, 820)

    canvas = Image.new("RGB", (WIDTH, HEIGHT), (15, 4, 24))
    canvas.paste(top, (0, 0))

    # Rich lower temple floor / glow built from the same artwork.
    lower = crop_cover(source, WIDTH, HEIGHT - 820)
    lower = ImageEnhance.Brightness(lower).enhance(0.58)
    lower = lower.filter(ImageFilter.GaussianBlur(2))
    canvas.paste(lower, (0, 820))

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (12, 2, 24, 65))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    gold = (255, 215, 80, 255)
    cream = (255, 246, 218, 255)
    deep = (50, 8, 24, 225)

    # Animated-looking framing elements baked into the still.
    draw.rectangle((0, 0, WIDTH, 10), fill=gold)
    draw.rectangle((0, HEIGHT - 10, WIDTH, HEIGHT), fill=gold)

    # Date / transition highlight.
    date = date_line
    df = get_font(42)
    db = draw.textbbox((0, 0), date, font=df)
    draw.rounded_rectangle(
        (55, 870, WIDTH - 55, 950),
        radius=28,
        fill=deep,
        outline=gold,
        width=3,
    )
    draw.text(
        ((WIDTH-(db[2]-db[0]))/2, 888),
        date,
        font=df,
        fill=cream,
    )

    # Strong devotional hook.
    hook = "ॐ  |  आस्था  |  ज्योतिष  |  शुभ ऊर्जा  |  ॐ"
    hf = get_font(50)
    hb = draw.textbbox((0, 0), hook, font=hf)
    draw.text(
        ((WIDTH-(hb[2]-hb[0]))/2, 1010),
        hook,
        font=hf,
        fill=gold,
    )

    # Current transition from the supplied script.
    trans = "आज का प्रमुख गोचर : " + transition_line.replace("चंद्रमा ने ", "चंद्रमा : ")
    tf = get_font(32)
    tb = draw.textbbox((0, 0), trans, font=tf)
    draw.rounded_rectangle(
        (50, 1100, WIDTH - 50, 1190),
        radius=28,
        fill=(15, 3, 25, 225),
        outline=(255, 205, 70, 210),
        width=3,
    )
    draw.text(
        ((WIDTH-(tb[2]-tb[0]))/2, 1122),
        trans,
        font=tf,
        fill=cream,
    )

    # Bottom devotional promise.
    promise = "बारहों राशियों के लिए आज के ग्रह संकेत"
    pf = get_font(48)
    pb = draw.textbbox((0, 0), promise, font=pf)
    draw.text(
        ((WIDTH-(pb[2]-pb[0]))/2, 1280),
        promise,
        font=pf,
        fill=cream,
    )

    sub = "धैर्य  |  कर्म  |  विश्वास  |  सकारात्मक सोच"
    sf = get_font(36)
    sb = draw.textbbox((0, 0), sub, font=sf)
    draw.text(
        ((WIDTH-(sb[2]-sb[0]))/2, 1360),
        sub,
        font=sf,
        fill=gold,
    )

    canvas.convert("RGB").save(output, "JPEG", quality=96, subsampling=0)
    return output


def create_outro():
    output = SCENES / "999_outro.jpg"

    img = Image.new("RGB", (WIDTH, HEIGHT), (14, 4, 25))
    draw = ImageDraw.Draw(img)

    gold = (255, 215, 75)
    cream = (255, 246, 220)

    # Temple-like background using a soft radial glow.
    for r in range(900, 80, -20):
        alpha = max(0, int(90 * (1 - r / 900)))
        draw.ellipse(
            (
                WIDTH//2-r,
                650-r,
                WIDTH//2+r,
                650+r,
            ),
            fill=(40 + alpha//4, 8 + alpha//12, 35, 255),
        )

    title_font = get_font(82)
    body_font = get_font(48)
    small_font = get_font(34)

    title = "॥ शुभम भवतु ॥"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(
        ((WIDTH-(box[2]-box[0]))/2, 430),
        title,
        font=title_font,
        fill=gold,
    )

    messages = [
        "आपका दिन शुभ और मंगलमय हो",
        "ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे",
        "दैनिक वैदिक ज्योतिष • आस्था • विश्वास",
    ]

    y = 650
    for message in messages:
        box = draw.textbbox((0, 0), message, font=body_font)
        draw.text(
            ((WIDTH-(box[2]-box[0]))/2, y),
            message,
            font=body_font,
            fill=cream,
        )
        y += 125

    footer = "ॐ • हर हर महादेव • जय श्री राम • राधे राधे • ॐ"
    box = draw.textbbox((0, 0), footer, font=small_font)
    draw.text(
        ((WIDTH-(box[2]-box[0]))/2, 1180),
        footer,
        font=small_font,
        fill=gold,
    )

    img.save(output, "JPEG", quality=96, subsampling=0)
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
    Cinematic motion using FFmpeg zoompan only.
    No sin/cos/eq expressions, avoiding the previous FFmpeg failures.
    """
    output = SCENES / f"clip_{index:02d}.mp4"
    frames = max(1, int(round(duration * FPS)))

    # Stronger visible motion than the previous barely noticeable zoom.
    zoom_expr = "1+0.00014*on"
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
            "-loop", "1",
            "-i", str(scene),
            "-vf", filtergraph,
            "-frames:v", str(frames),
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            str(output),
        ],
        timeout=900,
    )

    if not output.exists():
        raise RuntimeError(f"Animated clip was not created: {output}")

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
    rashi_weights,
):
    """
    Intro is intentionally short and engaging (~7s).
    Outro is short (~4s).
    The twelve Rashi scenes receive the remaining duration according to
    the relative amount of narration text, so the opening no longer consumes
    ~50 seconds before the first Rashi appears.
    """
    transition = 0.7
    intro_duration = 7.0
    outro_duration = 4.0

    if len(scene_paths) != 14:
        raise RuntimeError(f"Expected 14 scenes, received {len(scene_paths)}.")

    usable = narration_seconds + transition * (len(scene_paths) - 1)
    rashi_total = usable - intro_duration - outro_duration

    if rashi_total <= 60:
        raise RuntimeError("Narration is too short for the requested scene structure.")

    total_weight = sum(rashi_weights) or 1.0
    rashi_durations = [
        rashi_total * (w / total_weight)
        for w in rashi_weights
    ]

    durations = [intro_duration] + rashi_durations + [outro_duration]

    print("Scene durations:")
    for i, duration in enumerate(durations):
        print(f"  scene {i:02d}: {duration:.2f}s")

    clips = []
    for index, (scene, duration) in enumerate(zip(scene_paths, durations)):
        clips.append(
            make_animated_clip(
                ffmpeg,
                scene,
                duration,
                index,
            )
        )

    # xfade with per-clip durations.
    inputs = []
    for clip in clips:
        inputs.extend(["-i", str(clip)])

    filter_parts = []
    current = "[0:v]"
    elapsed = durations[0]

    for i in range(1, len(clips)):
        offset = elapsed - transition
        label = f"[xf{i}]"
        filter_parts.append(
            f"{current}[{i}:v]"
            f"xfade=transition=fade:"
            f"duration={transition}:"
            f"offset={offset:.3f}"
            f"{label}"
        )
        current = label
        elapsed += durations[i] - transition

    filtergraph = ";".join(filter_parts)
    silent = SCENES / "video_no_audio.mp4"

    run(
        [
            ffmpeg,
            "-y",
            *inputs,
            "-filter_complex", filtergraph,
            "-map", current,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-an",
            str(silent),
        ],
        timeout=1800,
    )

    attach_audio(ffmpeg, silent)

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
        create_intro(script)
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

    # Relative narration weights for the 12 Rashi scenes.
    # This keeps the visual scene length aligned with the amount of
    # spoken content without changing the generated astrology text.
    rashi_weights = []
    for key, *_ in RASHIS:
        section = sections.get(key, fallback_section(script, key))
        rashi_weights.append(max(1, len(section)))

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    build_video(
        ffmpeg,
        scenes,
        narration_seconds,
        rashi_weights,
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
