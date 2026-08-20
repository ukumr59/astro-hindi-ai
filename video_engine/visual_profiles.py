"""Data-only art direction for the premium AstroPratidin renderer.

The renderer consumes these profiles instead of hard-coding visual decisions in
scene code. This makes the daily output deterministic while allowing each
rashi to have a distinct visual rhythm without changing the approved brand
assets.
"""

RASHI_PROFILES = {
    "मेष": {"glyph": "♈", "element": "अग्नि", "planet": "मंगल", "hero_anchor": (0.44, 0.42), "pan": (-0.10, 0.06), "motion": "push_in"},
    "वृषभ": {"glyph": "♉", "element": "पृथ्वी", "planet": "शुक्र", "hero_anchor": (0.52, 0.44), "pan": (0.08, -0.04), "motion": "drift_right"},
    "मिथुन": {"glyph": "♊", "element": "वायु", "planet": "बुध", "hero_anchor": (0.48, 0.40), "pan": (-0.06, -0.06), "motion": "drift_left"},
    "कर्क": {"glyph": "♋", "element": "जल", "planet": "चंद्र", "hero_anchor": (0.50, 0.46), "pan": (0.05, 0.08), "motion": "push_in"},
    "सिंह": {"glyph": "♌", "element": "अग्नि", "planet": "सूर्य", "hero_anchor": (0.52, 0.40), "pan": (-0.08, 0.03), "motion": "drift_right"},
    "कन्या": {"glyph": "♍", "element": "पृथ्वी", "planet": "बुध", "hero_anchor": (0.46, 0.43), "pan": (0.07, -0.05), "motion": "drift_left"},
    "तुला": {"glyph": "♎", "element": "वायु", "planet": "शुक्र", "hero_anchor": (0.50, 0.42), "pan": (-0.05, 0.06), "motion": "push_in"},
    "वृश्चिक": {"glyph": "♏", "element": "जल", "planet": "मंगल", "hero_anchor": (0.54, 0.44), "pan": (0.09, 0.03), "motion": "drift_right"},
    "धनु": {"glyph": "♐", "element": "अग्नि", "planet": "बृहस्पति", "hero_anchor": (0.47, 0.40), "pan": (-0.07, -0.04), "motion": "drift_left"},
    "मकर": {"glyph": "♑", "element": "पृथ्वी", "planet": "शनि", "hero_anchor": (0.51, 0.45), "pan": (0.06, 0.07), "motion": "push_in"},
    "कुंभ": {"glyph": "♒", "element": "वायु", "planet": "शनि", "hero_anchor": (0.48, 0.41), "pan": (-0.09, -0.03), "motion": "drift_right"},
    "मीन": {"glyph": "♓", "element": "जल", "planet": "बृहस्पति", "hero_anchor": (0.53, 0.43), "pan": (0.05, -0.06), "motion": "drift_left"},
}

MOTION = {
    "intro": {"start": (0.50, 0.50), "end": (0.50, 0.50), "scale": 1.02},
    "push_in": {"start": (0.50, 0.50), "end": (0.50, 0.50), "scale": 1.10},
    "drift_right": {"start": (0.42, 0.50), "end": (0.58, 0.50), "scale": 1.08},
    "drift_left": {"start": (0.58, 0.50), "end": (0.42, 0.50), "scale": 1.08},
}
