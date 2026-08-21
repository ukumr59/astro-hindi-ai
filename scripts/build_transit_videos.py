"""Build branded advance-alert videos for major planetary transits.

A transit video is produced only when the current local date is exactly
seven calendar days before a detected major sign entry. The normal daily
12-Rashi production remains unchanged.
"""
from pathlib import Path
import asyncio
import json
import re
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageOps

OUT = Path("output")
QUEUE = OUT / "transit_publish_queue.json"
TRANSIT_OUT = OUT / "transit_uploads"
ASSET_LOGO = Path("assets/AstroPratidin Logo.png")
FONT = Path("assets/NotoSansDevanagari-Regular.ttf")
W, H, FPS = 1080, 1920, 30
VOICE = "hi-IN-SwaraNeural"
IST = ZoneInfo("Asia/Kolkata")

GOLD = (247, 202, 77, 255)
CREAM = (255, 244, 214, 255)
DARK = (25, 7, 34, 255)
PANEL = (31, 9, 38, 248)


def run(cmd):
    result = subprocess.run([str(x) for x in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1800)
    print(result.stdout[-6000:])
    if result.returncode:
        raise RuntimeError(result.stdout[-10000:])


def font(size):
    return ImageFont.truetype(str(FONT), size)


def fit(draw, text, max_width, size, minimum=20):
    for n in range(size, minimum - 1, -2):
        f = font(n)
        b = draw.textbbox((0, 0), text, font=f)
        if b[2] - b[0] <= max_width:
            return f
    return font(minimum)


def wrap(text, limit=34):
    lines, current = [], ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def center(draw, text, y, max_width, size, fill=CREAM, minimum=20):
    f = fit(draw, text, max_width, size, minimum)
    b = draw.textbbox((0, 0), text, font=f)
    draw.text(((W - (b[2] - b[0])) / 2, y), text, font=f, fill=fill)


def panel(draw, box):
    draw.rounded_rectangle(box, radius=32, fill=PANEL, outline=GOLD, width=2)


def slide_base():
    canvas = Image.new("RGBA", (W, H), DARK)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, W - 24, H - 24), radius=44, outline=GOLD, width=4)
    if ASSET_LOGO.exists():
        with Image.open(ASSET_LOGO).convert("RGBA") as logo:
            ratio = min(360 / logo.width, 220 / logo.height)
            logo = logo.resize((max(1, int(logo.width * ratio)), max(1, int(logo.height * ratio))), Image.Resampling.LANCZOS)
            canvas.alpha_composite(logo, ((W - logo.width) // 2, 52))
    return canvas, draw


def make_slides(event, out_dir):
    occurrence = datetime.fromisoformat(event["occurrence_ist"]).astimezone(IST)
    date_text = occurrence.strftime("%d-%m-%Y")
    time_text = occurrence.strftime("%H:%M IST")
    slides = []

    canvas, draw = slide_base()
    center(draw, "प्रमुख ग्रह गोचर", 340, W - 120, 66, GOLD)
    center(draw, "7 दिन पहले विशेष सूचना", 445, W - 120, 42, CREAM)
    panel(draw, (60, 610, W - 60, 1190))
    center(draw, event["planet_hi"], 690, W - 180, 70, GOLD)
    center(draw, "का राशि परिवर्तन", 800, W - 180, 42, CREAM)
    center(draw, f"{event['from_sign']} → {event['to_sign']}", 915, W - 180, 64, CREAM)
    center(draw, f"गोचर तिथि: {date_text}", 1035, W - 180, 38, GOLD)
    center(draw, f"समय: {time_text}", 1095, W - 180, 34, CREAM)
    center(draw, "AstroPratidin", 1510, W - 120, 38, GOLD)
    p1 = out_dir / "01_alert.jpg"; canvas.convert("RGB").save(p1, "JPEG", quality=98, subsampling=0); slides.append(p1)

    canvas, draw = slide_base()
    center(draw, "यह गोचर क्यों महत्वपूर्ण है?", 360, W - 120, 54, GOLD)
    panel(draw, (60, 560, W - 60, 1370))
    text = [
        f"{event['planet_hi']} का {event['from_sign']} से {event['to_sign']} में प्रवेश एक महत्वपूर्ण राशि परिवर्तन है।",
        "यह परिवर्तन सभी राशियों के लिए ग्रह-स्थिति के संदर्भ में नए संकेत सक्रिय करता है।",
        "व्यक्तिगत प्रभाव चंद्र राशि, लग्न और जन्म कुंडली के अनुसार अलग-अलग हो सकता है।",
    ]
    y = 680
    for paragraph in text:
        for line in wrap(paragraph, 38):
            center(draw, line, y, W - 160, 31, CREAM, 22)
            y += 50
        y += 34
    center(draw, "अगले 7 दिनों में इस गोचर पर विशेष ध्यान दें", 1510, W - 120, 31, GOLD)
    p2 = out_dir / "02_context.jpg"; canvas.convert("RGB").save(p2, "JPEG", quality=98, subsampling=0); slides.append(p2)

    canvas, draw = slide_base()
    center(draw, "विशेष ग्रह गोचर अलर्ट", 360, W - 120, 54, GOLD)
    panel(draw, (60, 560, W - 60, 1280))
    center(draw, f"{event['planet_hi']}", 690, W - 160, 70, GOLD)
    center(draw, f"{event['from_sign']} से {event['to_sign']}", 820, W - 160, 48, CREAM)
    center(draw, f"{date_text} • {time_text}", 930, W - 160, 38, CREAM)
    center(draw, "AstroPratidin पर जुड़े रहें", 1110, W - 160, 42, GOLD)
    center(draw, "दैनिक राशिफल और आगामी गोचर अपडेट के लिए", 1190, W - 160, 30, CREAM)
    center(draw, "फॉलो • सब्सक्राइब • शेयर", 1510, W - 160, 34, GOLD)
    p3 = out_dir / "03_close.jpg"; canvas.convert("RGB").save(p3, "JPEG", quality=98, subsampling=0); slides.append(p3)
    return slides


def narration(event):
    occurrence = datetime.fromisoformat(event["occurrence_ist"]).astimezone(IST)
    date_text = occurrence.strftime("%d %B %Y")
    time_text = occurrence.strftime("%H:%M IST")
    return (
        f"नमस्कार। AstroPratidin पर यह है प्रमुख ग्रह गोचर का विशेष अलर्ट। "
        f"{event['planet_hi']} का {event['from_sign']} से {event['to_sign']} राशि में प्रवेश होने वाला है। "
        f"यह महत्वपूर्ण राशि परिवर्तन {date_text} को लगभग {time_text} पर होगा। "
        f"हम इस गोचर की सूचना सात दिन पहले दे रहे हैं ताकि आप आने वाले परिवर्तन को समझने के लिए तैयार रहें। "
        f"इस गोचर का व्यक्तिगत प्रभाव चंद्र राशि, लग्न और जन्म कुंडली के अनुसार अलग-अलग हो सकता है। "
        f"AstroPratidin पर आगामी दिनों में इस गोचर से जुड़े राशिवार संकेत और दैनिक अपडेट देखते रहें। "
        f"वीडियो उपयोगी लगे तो फॉलो, सब्सक्राइब और शेयर करें। नमस्कार।"
    )


async def speak(text, path):
    await edge_tts.Communicate(text, VOICE, rate="+5%", volume="+0%").save(str(path))


def build_video(event):
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", event["id"]).strip("_")
    work = TRANSIT_OUT / f"work_{slug}"
    work.mkdir(parents=True, exist_ok=True)
    slides = make_slides(event, work)
    audio = work / "voice.mp3"
    asyncio.run(speak(narration(event), audio))
    durations = [4.0, 7.0, 5.0]
    concat = work / "slides.txt"
    with concat.open("w", encoding="utf-8") as fh:
        for slide, duration in zip(slides, durations):
            fh.write(f"file '{slide.resolve()}'\n")
            fh.write(f"duration {duration}\n")
        fh.write(f"file '{slides[-1].resolve()}'\n")
    output = TRANSIT_OUT / f"transit_{slug}.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
        "-i", audio, "-vf", "fps=30,format=yuv420p,setsar=1", "-c:v", "libx264",
        "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "128k",
        "-shortest", output,
    ])
    return output


def main():
    TRANSIT_OUT.mkdir(parents=True, exist_ok=True)
    if not QUEUE.exists():
        raise SystemExit("transit_publish_queue.json missing")
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    events = queue.get("events", [])
    # Clean only generated transit MP4s from this run; work directories are retained
    # until the final artifact is packaged for debugging.
    for path in TRANSIT_OUT.glob("transit_*.mp4"):
        path.unlink()
    manifest = []
    for event in events:
        output = build_video(event)
        manifest.append({**event, "video_path": str(output)})
        print(f"TRANSIT VIDEO BUILT: {output}")
    (OUT / "transit_video_manifest.json").write_text(json.dumps({"events": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"TRANSIT VIDEO BUILD: PASS — {len(manifest)} video(s)")


if __name__ == "__main__":
    main()
