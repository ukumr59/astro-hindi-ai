"""
Hindi daily content engine for the Vedic / Jyotisha system.

The script is designed for a mass daily horoscope.

Reference:
    Chandra Rashi / Moon-sign based gochara

Method:
    Nirayana / sidereal planetary positions
    + Lahiri ayanamsha
    + classical graha gochara tendencies
    + graha drishti
    + retrograde modifiers
    + detected sign-change events

The output is intentionally concise enough for approximately
2–3 minutes of Hindi narration.
"""

from datetime import datetime

from astro_engine.rules import (
    SIGN_HI,
    PLANET_HI,
    interpret_for_rashi,
    rashi_summary,
)


# ============================================================
# CONTENT SETTINGS
# ============================================================

MAX_WORDS_APPROX = 500

IMPORTANT_PLANETS = {
    "Jupiter",
    "Saturn",
    "Rahu",
    "Ketu",
    "Mars",
    "Venus",
    "Mercury",
    "Sun",
    "Moon",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def planet_name(planet):
    return PLANET_HI.get(
        planet,
        planet
    )


def format_position(position):
    """
    Convert a planetary position into natural Hindi.
    """

    name = planet_name(position.planet)

    sign = SIGN_HI[
        position.sign_index
    ]

    retrograde = ""

    if position.retrograde and position.planet not in {
        "Rahu",
        "Ketu",
    }:
        retrograde = " (वक्री)"

    return (
        f"{name} {position.longitude:.2f}° "
        f"{sign}{retrograde}"
    )


def event_lines(events):
    """
    Convert detected planetary sign-change events into
    concise Hindi narration.
    """

    if not events:
        return [
            "आज कोई प्रमुख ग्रह राशि परिवर्तन दर्ज नहीं हुआ है।"
        ]

    lines = []

    for event in events[:4]:

        lines.append(
            f"{event.description_hi}"
        )

    return lines


def importance_score(item):
    """
    Ranking helper for planetary influences.
    """

    return abs(
        item.get("score", 0)
    )


def overall_rashi_label(score):
    """
    Convert numerical Vedic transit score into a
    viewer-friendly Hindi label.
    """

    if score >= 4:
        return "अनुकूल"

    if score <= -4:
        return "सावधानी"

    return "मिश्रित"


def short_influence_text(influence):
    """
    Keep individual planetary interpretation short enough
    for a 2–3 minute video.
    """

    text = influence["text"]

    # Prevent excessively long individual sections.
    sentences = text.split("।")

    sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]

    if len(sentences) > 2:
        sentences = sentences[:2]

    return "। ".join(sentences) + "।"


# ============================================================
# DAILY SCRIPT
# ============================================================

def build_daily_script(date, positions, events):
    """
    Build the complete Hindi daily astrology script.

    The resulting script is designed to be consumed by the
    future video engine and Hindi voice engine.
    """

    lines = []

    # --------------------------------------------------------
    # INTRO
    # --------------------------------------------------------

    lines.append(
        "नमस्कार! स्वागत है आपके आज के दैनिक वैदिक "
        "ज्योतिष अपडेट में।"
    )

    lines.append(
        "आज हम देखेंगे वर्तमान ग्रह स्थिति, महत्वपूर्ण "
        "गोचर और चंद्र राशि के आधार पर सभी बारह राशियों "
        "पर उनके संभावित प्रभाव।"
    )

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if isinstance(date, datetime):
        date_text = date.strftime(
            "%d-%m-%Y"
        )
    else:
        date_text = str(date)

    lines.append(
        f"आज की तारीख है {date_text}।"
    )

    # --------------------------------------------------------
    # PLANETARY POSITIONS
    # --------------------------------------------------------

    lines.append(
        "सबसे पहले जानते हैं वर्तमान ग्रह स्थिति।"
    )

    for position in positions:

        lines.append(
            format_position(position)
        )

    # --------------------------------------------------------
    # IMPORTANT TRANSITIONS
    # --------------------------------------------------------

    lines.append(
        "अब बात करते हैं आज के महत्वपूर्ण ग्रह परिवर्तनों की।"
    )

    lines.extend(
        event_lines(events)
    )

    # --------------------------------------------------------
    # RASHI ANALYSIS
    # --------------------------------------------------------

    lines.append(
        "अब शुरू करते हैं बारह राशियों का संक्षिप्त "
        "वैदिक गोचर विश्लेषण।"
    )

    rashi_results = []

    for rashi_index in range(12):

        summary = rashi_summary(
            rashi_index,
            positions
        )

        rashi_results.append(
            summary
        )

    # --------------------------------------------------------
    # MOST IMPORTANT RASHIS
    # --------------------------------------------------------

    positive_rashis = sorted(
        rashi_results,
        key=lambda item: item["score"],
        reverse=True
    )

    cautious_rashis = sorted(
        rashi_results,
        key=lambda item: item["score"]
    )

    # --------------------------------------------------------
    # ALL 12 RASHIS
    # --------------------------------------------------------

    for summary in rashi_results:

        rashi = summary["rashi"]

        score = summary["score"]

        label = overall_rashi_label(
            score
        )

        lines.append(
            f"{rashi राशि — {label}।"
        )

        # Take the two strongest influences.
        influences = sorted(
            summary["influences"],
            key=importance_score,
            reverse=True
        )

        selected = influences[:2]

        for influence in selected:

            text = short_influence_text(
                influence
            )

            lines.append(
                text
            )

    # --------------------------------------------------------
    # BEST RASHIS
    # --------------------------------------------------------

    best = [
        item["rashi"]
        for item in positive_rashis[:3]
        if item["score"] > 0
    ]

    if best:

        lines.append(
            "आज के गोचर में अपेक्षाकृत बेहतर संकेत "
            f"{', '.join(best)} राशि के लिए दिखाई दे रहे हैं।"
        )

    # --------------------------------------------------------
    # CAUTION RASHIS
    # --------------------------------------------------------

    caution = [
        item["rashi"]
        for item in cautious_rashis[:3]
        if item["score"] < 0
    ]

    if caution:

        lines.append(
            "वहीं "
            f"{', '.join(caution)} राशि वालों को "
            "आज जल्दबाजी से बचते हुए निर्णय लेने की सलाह है।"
        )

    # --------------------------------------------------------
    # GENERAL ADVICE
    # --------------------------------------------------------

    lines.append(
        "याद रखें, दैनिक गोचर सामान्य संकेत देता है। "
        "व्यक्तिगत फलादेश के लिए जन्म तिथि, जन्म समय, "
        "जन्म स्थान और पूरी जन्म कुंडली का अध्ययन आवश्यक होता है।"
    )

    # --------------------------------------------------------
    # DISCLAIMER / RESPONSIBLE CONTENT
    # --------------------------------------------------------

    lines.append(
        "इन ज्योतिषीय संकेतों को निश्चित भविष्यवाणी के "
        "बजाय पारंपरिक वैदिक ज्योतिष के मार्गदर्शन के रूप "
        "में देखें।"
    )

    # --------------------------------------------------------
    # CTA
    # --------------------------------------------------------

    lines.append(
        "अगर आपको यह दैनिक वैदिक ज्योतिष अपडेट उपयोगी लगा, "
        "तो चैनल को सब्सक्राइब करें और वीडियो को लाइक करें।"
    )

    lines.append(
        "कल फिर मिलेंगे नए ग्रह गोचर और आपकी राशि के "
        "नए संकेतों के साथ। नमस्कार!"
    )

    return "\n".join(lines)
