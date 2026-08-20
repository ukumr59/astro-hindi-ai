"""Stable entrypoint for the audio-led devotional renderer.

This wrapper replaces only the FFmpeg motion function that previously emitted
an invalid zoompan filter expression. The renderer's narration, scene,
audio-sync, concatenation, and validation logic remain unchanged.
"""

import subprocess

import imageio_ffmpeg

from . import render_sync as renderer


def motion(ffmpeg, scene, seconds, index):
    """Render one still scene with a safe cinematic zoom and fade.

    The previous expression used a comma inside zoompan's z expression,
    which FFmpeg interpreted as a filter separator. This version deliberately
    uses expressions without commas and keeps the zoom within ~1.13x.
    """
    output = renderer.SCENES / f"motion_{index:02d}.mp4"
    frames = max(2, round(seconds * renderer.FPS))
    zoom_step = 0.13 / max(1, frames)

    if index % 2 == 0:
        x = f"(iw-iw/zoom)*(on/{frames})"
    else:
        x = f"(iw-iw/zoom)*(({frames}-on)/{frames})"
    y = "(ih-ih/zoom)/2"

    fade = min(0.28, max(0.10, seconds / 6))
    fade_out_start = max(0.05, seconds - fade)

    filtergraph = (
        f"zoompan=z=1+{zoom_step:.10f}*on:"
        f"x={x}:y={y}:d=1:s={renderer.W}x{renderer.H}:fps={renderer.FPS},"
        f"fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade:.3f}"
    )

    renderer.run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            scene,
            "-vf",
            filtergraph,
            "-t",
            f"{seconds:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            output,
        ],
        900,
    )
    return output


def main():
    # render_sync.main() resolves motion() from its module globals. Replace
    # that one function before invoking the otherwise unchanged pipeline.
    renderer.motion = motion
    renderer.main()


if __name__ == "__main__":
    main()
