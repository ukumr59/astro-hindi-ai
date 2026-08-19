# Astro Hindi Automation — v0.1

Foundation for a cloud-first, zero-subscription-target Hindi astrology video system.

Hard requirements:
- Hindi output
- Main video ~2–3 minutes
- Important planetary transitions + 12-rashi impact
- Automatic script → voice → video
- Automatic YouTube + Facebook publishing
- No routine human posting
- No essential dependency on the user's computer
- ₹0/month recurring-cost target
- Version-controlled and recoverable

This v0.1 is a foundation/prototype. It deliberately uses a replaceable
ephemeris interface until the production ephemeris/license is selected.

Run:
  python -m astro_engine.main

The production target is GitHub Actions + official platform APIs + local/offline
TTS/video tooling.
