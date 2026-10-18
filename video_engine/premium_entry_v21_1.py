"""V21 production entrypoint with resilient rendering and date-driven visual diversity."""
from pathlib import Path
import json
from . import premium_entry as v21
from . import render_sync as base
from .visual_profiles import RASHI_PROFILES, MOTION


VISUAL_PALETTES = {
    "classic": {"gold": (247, 202, 77, 255), "cream": (255, 244, 214, 255), "dark": (25, 7, 34, 255), "panel": (31, 9, 38, 248)},
    "sunrise": {"gold": (255, 181, 71, 255), "cream": (255, 239, 207, 255), "dark": (51, 18, 25, 255), "panel": (67, 24, 32, 248)},
    "midnight": {"gold": (155, 198, 255, 255), "cream": (235, 243, 255, 255), "dark": (8, 16, 42, 255), "panel": (12, 25, 57, 248)},
    "orbit": {"gold": (182, 147, 255, 255), "cream": (247, 239, 255, 255), "dark": (25, 10, 48, 255), "panel": (42, 19, 72, 248)},
    "earth": {"gold": (123, 205, 143, 255), "cream": (237, 247, 226, 255), "dark": (12, 38, 30, 255), "panel": (20, 57, 43, 248)},
    "aurora": {"gold": (102, 222, 202, 255), "cream": (230, 255, 249, 255), "dark": (8, 34, 43, 255), "panel": (14, 61, 68, 248)},
    "lotus": {"gold": (255, 151, 193, 255), "cream": (255, 239, 247, 255), "dark": (52, 10, 35, 255), "panel": (76, 19, 52, 248)},
}


def _content_profile():
    path = base.OUT / "content_profile.json"
    if not path.exists():
        return {"visual_style": "classic"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid content diversity profile: {exc}")


def _apply_visual_style():
    profile = _content_profile()
    style = profile.get("visual_style", "classic")
    palette = VISUAL_PALETTES.get(style)
    if palette is None:
        raise RuntimeError(f"Unknown visual diversity style: {style}")
    v21.GOLD = palette["gold"]
    v21.GOLD_SOFT = (*palette["gold"][:3], 215)
    v21.CREAM = palette["cream"]
    v21.DARK = palette["dark"]
    v21.PANEL = palette["panel"]
    print(f"VISUAL DIVERSITY: style={style} profile={profile.get('key', 'unknown')}")
    return style


def _normalize_sar(ffmpeg, out):
    src = Path(out)
    tmp = src.with_name(src.stem + ".sar-normalized.mp4")
    vf = f"scale={base.W}:{base.H},setsar=1,format=yuv420p"
    base.run([ffmpeg, "-y", "-i", src, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", tmp], 900)
    tmp.replace(src)


def _encode_motion(ffmpeg, scene, out, seconds, profile, *, safe=False):
    seconds = max(0.5, float(seconds))
    frames = max(2, int(round(seconds * base.FPS)))
    scale = float(profile["scale"])
    sw = int(base.W * scale) // 2 * 2
    sh = int(base.H * scale) // 2 * 2
    sx, sy = profile["start"]
    ex, ey = profile["end"]
    if safe:
        scale = max(1.04, min(scale, 1.08)); sw = int(base.W * scale) // 2 * 2; sh = int(base.H * scale) // 2 * 2
        x = "(iw-ow)*0.50"; y = "(ih-oh)*0.50"
    else:
        x = f"(iw-ow)*({sx:.4f}+({ex:.4f}-{sx:.4f})*n/{frames-1})"
        y = f"(ih-oh)*({sy:.4f}+({ey:.4f}-{sy:.4f})*n/{frames-1})"
    fade = min(0.30, max(0.12, seconds / 8)); fade_out = max(0.05, seconds - fade)
    vf = f"scale={sw}:{sh}:force_original_aspect_ratio=disable,crop={base.W}:{base.H}:x='{x}':y='{y}',fps={base.FPS},fade=t=in:st=0:d={fade:.3f},fade=t=out:st={fade_out:.3f}:d={fade:.3f}"
    base.run([ffmpeg, "-y", "-loop", "1", "-i", scene, "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", out], 900)
    _normalize_sar(ffmpeg, out)


def motion_profile(index):
    if index == 0 or index == len(base.RASHIS) + 1:
        return MOTION["intro"]
    rashi_index = index - 1
    if not 0 <= rashi_index < len(base.RASHIS):
        raise RuntimeError(f"Invalid motion scene index: {index}")
    key = base.RASHIS[rashi_index][0]
    return MOTION[RASHI_PROFILES[key]["motion"]]


def hardened_motion(ffmpeg, scene, seconds, index):
    out = base.SCENES / f"motion_{index:02d}.mp4"
    profile = motion_profile(index)
    try:
        _encode_motion(ffmpeg, scene, out, seconds, profile, safe=False)
    except RuntimeError as exc:
        print(f"PRIMARY MOTION ENCODE FAILED FOR SEGMENT {index}: {exc}")
        _encode_motion(ffmpeg, scene, out, seconds, profile, safe=True)
    return out


def main():
    if set(RASHI_PROFILES) != {x[0] for x in base.RASHIS}:
        raise RuntimeError("Rashi visual-profile coverage mismatch")
    if set(MOTION) != {"intro", "push_in", "drift_right", "drift_left"}:
        raise RuntimeError("Motion profile coverage mismatch")
    _apply_visual_style()
    base.intro = v21.premium_intro
    base.rashi_scene = v21.premium_rashi
    base.outro = v21.premium_outro
    base.motion = hardened_motion
    base.main()


if __name__ == "__main__":
    main()
