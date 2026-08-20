"""V21.4.2 production entrypoint with resilient premium motion rendering."""
from pathlib import Path
from . import premium_entry as v21
from . import render_sync as base
from .visual_profiles import RASHI_PROFILES, MOTION


def _normalize_sar(ffmpeg, out):
    """Normalize each generated motion MP4 before the shared concat stage."""
    src = Path(out)
    tmp = src.with_name(src.stem + ".sar-normalized.mp4")
    vf = f"scale={base.W}:{base.H},setsar=1,format=yuv420p"
    base.run([
        ffmpeg, "-y", "-i", src,
        "-vf", vf,
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", tmp
    ], 900)
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
        scale = max(1.04, min(scale, 1.08))
        sw = int(base.W * scale) // 2 * 2
        sh = int(base.H * scale) // 2 * 2
        x = "(iw-ow)*0.50"
        y = "(ih-oh)*0.50"
    else:
        x = f"(iw-ow)*({sx:.4f}+({ex:.4f}-{sx:.4f})*n/{frames-1})"
        y = f"(ih-oh)*({sy:.4f}+({ey:.4f}-{sy:.4f})*n/{frames-1})"

    fade = min(0.30, max(0.12, seconds / 8))
    fade_out = max(0.05, seconds - fade)
    vf = (
        f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
        f"crop={base.W}:{base.H}:x='{x}':y='{y}',"
        f"fps={base.FPS},"
        f"fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={fade_out:.3f}:d={fade:.3f}"
    )
    base.run([
        ffmpeg, "-y", "-loop", "1", "-i", scene,
        "-vf", vf, "-frames:v", str(frames),
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", out
    ], 900)
    _normalize_sar(ffmpeg, out)


def motion_profile(index):
    """Resolve the 14-scene timeline without indexing past the 12 Rashis."""
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
        print(f"RETRYING SEGMENT {index} WITH GUARANTEED-SAFE PREMIUM FALLBACK")
        _encode_motion(ffmpeg, scene, out, seconds, profile, safe=True)
    return out


def main():
    if set(RASHI_PROFILES) != {x[0] for x in base.RASHIS}:
        raise RuntimeError("Rashi visual-profile coverage mismatch")
    if set(MOTION) != {"intro", "push_in", "drift_right", "drift_left"}:
        raise RuntimeError("Motion profile coverage mismatch")
    base.intro = v21.premium_intro
    base.rashi_scene = v21.premium_rashi
    base.outro = v21.premium_outro
    base.motion = hardened_motion
    base.main()


if __name__ == "__main__":
    main()
