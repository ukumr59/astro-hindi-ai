# System architecture

Planetary data
  ↓
Ephemeris adapter
  ↓
Transit/event detector
  ↓
Astrology rules engine
  ↓
12-rashi impact engine
  ↓
Hindi content engine
  ↓
Offline Hindi TTS
  ↓
FFmpeg video factory
  ↓
 ┌───────────────┐
 ↓               ↓
YouTube        Facebook
 ↓               ↓
Analytics ───────┘
  ↓
Content scoring / next-day planning

The user's computer is not a runtime dependency.
