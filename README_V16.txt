DAILY ASTRO HINDI VIDEO — V16

This package replaces the broken/incomplete renderer and is intended to be copied into the ROOT of the existing astro-hindi-ai repository.

WHAT V16 DOES
- Uses only bundled 1600x1600 deity artwork. No Wikimedia, museum, Picryl, or other remote deity downloads.
- Includes HD devotional artwork for Hanuman, Lakshmi, Ganesha, Shiva, Surya, Vishnu and Shani.
- Uses a premium temple/diya devotional opening.
- Displays the deity prominently in each Rashi scene.
- Does NOT print the deity's name underneath the deity artwork.
- Uses visible slow cinematic zoom/pan on every scene.
- Uses cross-fade transitions between intro, all 12 Rashi scenes and outro.
- Uses Devanagari font bundled locally.
- Includes the previously missing prepare_deities() function.
- Avoids the FFmpeg sin()/brightness filter expression that caused the earlier exit-code-234 failure.

FILES TO REPLACE/MERGE
- video_engine/render.py
- assets/NotoSansDevanagari-Regular.ttf
- assets/intro_devotional.jpg
- assets/deities/*.jpg

DO NOT delete the existing content_engine, astro_engine, config, publishers, .github, etc. V16 is a renderer/assets replacement package, not a replacement for the entire application.

EXPECTED DEITY LOG
Using bundled HD deity artwork: Hanuman
Using bundled HD deity artwork: Lakshmi goddess
Using bundled HD deity artwork: Ganesha
Using bundled HD deity artwork: Shiva Hindu god
Using bundled HD deity artwork: Surya Hindu god
Using bundled HD deity artwork: Vishnu Hindu god
Using bundled HD deity artwork: Shani Hindu god

There must be NO remote deity-image download attempts.
