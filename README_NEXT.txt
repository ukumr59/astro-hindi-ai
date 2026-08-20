ASTRO HINDI V14 UPDATE

Replace/add these files at the repository root:

video_engine/render.py
assets/intro_devotional.jpg
assets/NotoSansDevanagari-Regular.ttf
assets/deities/hanuman.jpg
assets/deities/lakshmi.jpg
assets/deities/ganesha.jpg
assets/deities/shiva.jpg
assets/deities/surya.jpg
assets/deities/vishnu.jpg
assets/deities/shani.jpg

No changes to daily.yml are required.

This version:
- uses bundled devotional deity artwork; no runtime deity-image downloads
- uses all seven deity assets in the Rashi mapping
- removes deity names from below the artwork
- gives each Rashi a prominent devotional hero image
- adds a bright temple-style opening
- makes the opening short (about 7 seconds)
- uses variable Rashi scene durations based on script length
- uses cinematic zoom and cross-fade transitions
- keeps the daily date and Moon transition dynamic from daily_script.md
- bundles the Devanagari font so scene rendering does not depend on a font download
