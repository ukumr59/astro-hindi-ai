"""
Daily Hindi Vedic Jyotisha content engine.

Pipeline:

    Ephemeris
        ↓
    Nirayana / Lahiri planetary positions
        ↓
    Chandra Rashi
        ↓
    Classical Gochar rules
        ↓
    Rashi classification
        ↓
    Hindi narration
"""

from datetime import datetime

from astro_engine.rules import (
    rashi_summary,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def date_text(date):
    if isinstance(date, datetime):
        return date.strftime("%d-%m-%Y")

    return str(date)


def clean_text(text):
    if not text:
        return ""

    text = text.replace(
        "।।",
        "।"
    )

    text = text.replace(
        "  ",
        " "
    )

    return text.strip()


# ============================================================
# EVENT NARRATION
# ============================================================

def build_event_section(events):

    lines = []

    lines.append(
        "आज के प्रमुख ग्रह परिवर्तन:"
    )

    if not events:

        lines.append(
            "आज कोई प्रमुख राशि परिवर्तन दर्ज नहीं हुआ है। "
            "इसलिए वर्तमान ग्रह स्थितियों के आधार पर "
            "दैनिक गोचर के संकेत देखेंगे।"
        )

        return lines

    count = 0

    for event in events:

        if count >= 4:
            break

        description = getattr(
            event,
            "description_hi",
            ""
        )

        if description:

            lines.append(
                clean_text(
                    description
                )
            )

            count += 1

    if count == 0:

        lines.append(
            "आज कोई प्रमुख राशि परिवर्तन दर्ज नहीं हुआ है।"
        )

    return lines


# ============================================================
# INFLUENCE SELECTION
# ============================================================

def strongest_influences(
    summary,
    limit=2
):

    influences = summary.get(
        "influences",
        []
    )

    # rules.py has already ranked these,
    # but sorting again makes this function robust.
    ranked = sorted(
        influences,
        key=lambda item: (
            abs(
                item.get(
                    "score",
                    0
                )
            ),
            item.get(
                "score",
                0
            )
        ),
        reverse=True
    )

    return ranked[:limit]


# ============================================================
# OVERALL RASHI NARRATION
# ============================================================

def overall_sentence(
    summary
):

    overall = summary.get(
        "overall",
        "मिश्रित"
    )

    if overall == "अनुकूल":

        return (
            "आज के प्रमुख ग्रह गोचर इस राशि के लिए "
            "कुल मिलाकर अनुकूल संकेत दे रहे हैं।"
        )

    if overall == "सावधानी":

        return (
            "आज के प्रमुख ग्रह गोचर इस राशि के लिए "
            "सावधानी और धैर्य रखने का संकेत दे रहे हैं।"
        )

    return (
        "आज के प्रमुख ग्रह गोचर इस राशि के लिए "
        "मिश्रित संकेत दे रहे हैं। इसलिए संतुलित "
        "दृष्टिकोण रखना बेहतर रहेगा।"
    )


# ============================================================
# PRACTICAL ADVICE
# ============================================================

def practical_advice(
    summary
):

    overall = summary.get(
        "overall",
        "मिश्रित"
    )

    if overall == "अनुकूल":

        return (
            "करियर में आगे बढ़ने के अवसरों का लाभ लें। "
            "धन के मामलों में योजनाबद्ध निर्णय करें और "
            "रिश्तों में सकारात्मक संवाद बनाए रखें।"
        )

    if overall == "सावधानी":

        return (
            "करियर में जल्दबाजी से बचें। "
            "धन संबंधी मामलों में अनावश्यक जोखिम न लें "
            "और रिश्तों में धैर्य बनाए रखें।"
        )

    return (
        "करियर और धन में संतुलित निर्णय लें। "
        "रिश्तों में स्पष्ट संवाद रखें और "
        "महत्वपूर्ण मामलों में जल्दबाजी से बचें।"
    )


# ============================================================
# ONE RASHI
# ============================================================

def build_rashi_section(
    summary
):

    rashi = summary.get(
        "rashi",
        "राशि"
    )

    lines = []

    # --------------------------------------------------------
    # HEADING
    # --------------------------------------------------------

    lines.append(
        f"{rashi} राशि:"
    )

    # --------------------------------------------------------
    # OVERALL CLASSIFICATION
    # --------------------------------------------------------

    lines.append(
        overall_sentence(
            summary
        )
    )

    # --------------------------------------------------------
    # STRONGEST PLANETS
    # --------------------------------------------------------

    influences = strongest_influences(
        summary,
        limit=2
    )

    for influence in influences:

        text = influence.get(
            "text",
            ""
        )

        if text:

            lines.append(
                clean_text(
                    text
                )
            )

    # --------------------------------------------------------
    # PRACTICAL ADVICE
    # --------------------------------------------------------

    lines.append(
        practical_advice(
            summary
        )
    )

    return " ".join(
        lines
    )


# ============================================================
# HIGHLIGHTS
# ============================================================

def build_highlights(
    summaries
):

    lines = []

    favourable = [
        summary["rashi"]
        for summary in summaries
        if summary.get(
            "overall"
        ) == "अनुकूल"
    ]

    cautious = [
        summary["rashi"]
        for summary in summaries
        if summary.get(
            "overall"
        ) == "सावधानी"
    ]

    if favourable:

        lines.append(
            "आज अपेक्षाकृत अनुकूल संकेत "
            + ", ".join(
                favourable[:4]
            )
            + " राशि के लिए दिखाई दे रहे हैं।"
        )

    if cautious:

        lines.append(
            "वहीं "
            + ", ".join(
                cautious[:4]
            )
            + " राशि वालों को "
            "आज धैर्य और सावधानी रखने की सलाह है।"
        )

    return lines


# ============================================================
# COMPLETE DAILY SCRIPT
# ============================================================

def build_daily_script(
    date,
    positions,
    events
):

    lines = []

    # ========================================================
    # INTRO
    # ========================================================

    lines.append(
        "नमस्कार! स्वागत है आपके दैनिक "
        "वैदिक ज्योतिष अपडेट में।"
    )

    lines.append(
        "आज हम निरयन ग्रह स्थिति और चंद्र राशि "
        "के आधार पर बारहों राशियों के लिए "
        "प्रमुख गोचर संकेत जानेंगे।"
    )

    lines.append(
        f"आज की तारीख है {date_text(date)}।"
    )

    # ========================================================
    # EVENTS
    # ========================================================

    lines.extend(
        build_event_section(
            events
        )
    )

    # ========================================================
    # CALCULATE ALL RASHIS
    # ========================================================

    summaries = []

    for rashi_index in range(12):

        summary = rashi_summary(
            rashi_index,
            positions
        )

        summaries.append(
            summary
        )

    # ========================================================
    # RASHI INTRO
    # ========================================================

    lines.append(
        "अब जानते हैं बारहों चंद्र राशियों पर "
        "आज के ग्रह गोचर का प्रभाव।"
    )

    # ========================================================
    # ALL 12 RASHIS
    # ========================================================

    for summary in summaries:

        lines.append(
            build_rashi_section(
                summary
            )
        )

    # ========================================================
    # DAILY HIGHLIGHTS
    # ========================================================

    lines.extend(
        build_highlights(
            summaries
        )
    )

    # ========================================================
    # DISCLAIMER
    # ========================================================

    lines.append(
        "यह सामान्य चंद्र राशि आधारित वैदिक "
        "गोचर विश्लेषण है। व्यक्तिगत फलादेश के लिए "
        "जन्म कुंडली, दशा और अन्य ज्योतिषीय कारकों "
        "का अध्ययन आवश्यक होता है।"
    )

    # ========================================================
    # CLOSING
    # ========================================================

    lines.append(
        "अगर यह दैनिक वैदिक ज्योतिष अपडेट उपयोगी लगा "
        "तो वीडियो को लाइक करें और चैनल को सब्सक्राइब करें।"
    )

    lines.append(
        "कल फिर मिलेंगे नए ग्रह गोचर और नई जानकारी के साथ। "
        "नमस्कार!"
    )

    return "\n".join(
        lines
    )
