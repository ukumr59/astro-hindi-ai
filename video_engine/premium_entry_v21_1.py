"""V21.1 production entrypoint with hardened FFmpeg motion."""
from . import premium_entry as v21
from . import render_sync as base
from .visual_profiles import RASHI_PROFILES, MOTION


def hardened_motion(ffmpeg, scene, seconds, index):
    out = base.SCENES / f"motion_{index:02d}.mp4"
    seconds = max(0.5, float(seconds))
    profile = MOTION["intro"] if index == 0 else MOTION[RASHI_PROFILES[base.RASHIS[index - 1][0]]["motion"]]
    scale = float(profile["scale"])
    sw = int(base.W * scale) // 2 * 2
    sh = int(base.H * scale) // 2 * 2
    sx, sy = profile["start"]
    ex, ey = profile["end"]
    progress = f"clip(t/{seconds:.6f},0,1)"
    x = f"clip((in_w-out_w)*({sx:.4f}+({ex:.4f}-{sx:.4f})*{progress}),0,in_w-out_w)"
    y = f"clip((in_h-out_h)*({sy:.4f}+({ey:.4f}-{sy:.4f})*{progress}),0,in_h-out_h)"
    fade = min(0.30, max(0.12, seconds / 8))
    fade_out = max(0.05, seconds - fade)
    vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
          f"crop={base.W}:{base.H}:x='{x}':y='{y}',"
          f"fps={base.FPS},fade=t=in:st=0:d={fade:.3f},"
          f"fade=t=out:st={fade_out:.3f}:d={fade:.3f}")
    base.run([ffmpeg, "-y", "-loop", "1", "-i", scene, "-vf", vf,
              "-t", f"{seconds:.3f}", "-an", "-c:v", "libx264",
              "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
              "-threads", "2", out], 900)
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
