"""
Daily Hindi Vedic Jyotisha content engine.

Reference:
    Chandra Rashi / Moon-sign based Gochar

Method:
    Nirayana / Sidereal positions
    Lahiri ayanamsha
    Classical Gochar houses
    Graha-specific interpretations
    Retrograde modifiers
    Detected sign-change events

Target:
    Approximately 2–3 minutes of Hindi narration.
"""

from datetime import datetime

from astro_engine.rules import (
    SIGN_HI,
    PLANET_HI,
    rashi_summary,
)


# ============================================================
# PLANET PRIORITY
# ============================================================

PLANET_PRIORITY = {
    "Saturn": 10,
    "Jupiter": 10,
    "Rahu": 9,
    "Ketu": 9,
    "Mars": 8,
    "Sun": 7,
    "Venus": 6,
    "Mercury": 6,
    "Moon": 5,
}


# ============================================================
# HOUSE MEANINGS
# ============================================================

HOUSE_MEANING = {
    1: "स्वास्थ्य और व्यक्तित्व",
    2: "धन, परिवार और वाणी",
    3: "साहस, प्रयास और संचार",
    4: "घर, संपत्ति और मानसिक सुख",
    5: "शिक्षा, प्रेम और संतान",
    6: "नौकरी, प्रतियोगिता और स्वास्थ्य",
    7: "विवाह और साझेदारी",
    8: "अचानक परिवर्तन और साझा धन",
    9: "भाग्य, धर्म और उच्च शिक्षा",
    10: "करियर और प्रतिष्ठा",
    11: "आय, लाभ और इच्छापूर्ति",
    12: "खर्च, विदेश और एकांत",
}


# ============================================================
# PLANET THEMES
# ============================================================

PLANET_THEME = {
    "Sun": "आत्मविश्वास और नेतृत्व",
    "Moon": "मन और भावनाएं",
    "Mars": "ऊर्जा और साहस",
    "Mercury": "बुद्धि और संचार",
    "Jupiter": "ज्ञान, विस्तार और अवसर",
    "Venus": "प्रेम और सुख-सुविधाएं",
    "Saturn": "कर्म, अनुशासन और जिम्मेदारी",
    "Rahu": "महत्वाकांक्षा और नए अवसर",
    "Ketu": "वैराग्य और आध्यात्मिक चिंतन",
}


# ============================================================
# HINDI HELPERS
# ============================================================

def planet_name(planet):
    return PLANET_HI.get(
        planet,
        planet
    )


def ordinal_house(house):
    names = {
        1: "पहले",
        2: "दूसरे",
        3: "तीसरे",
        4: "चौथे",
        5: "पांचवें",
        6: "छठे",
        7: "सातवें",
        8: "आठवें",
        9: "नौवें",
        10: "दसवें",
        11: "ग्यारहवें",
        12: "बारहवें",
    }

    return names.get(
        house,
        str(house)
    )


def clean(text):
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
# PLANETARY POSITION
# ============================================================

def format_position(position):

    name = planet_name(
        position.planet
    )

    sign = SIGN_HI[
        position.sign_index
    ]

    retro = ""

    if (
        position.retrograde
        and position.planet not in {
            "Rahu",
            "Ketu"
        }
    ):
        retro = " वक्री"

    return (
        f"{name} {sign} राशि में "
        f"{position.longitude:.1f} डिग्री{retro}"
    )


# ============================================================
# TRANSITION EVENTS
# ============================================================

def format_events(events):

    if not events:
        return (
            "आज कोई प्रमुख ग्रह राशि परिवर्तन नहीं हुआ है।"
        )

    result = []

    for event in events[:3]:

        text = getattr(
            event,
            "description_hi",
            ""
        )

        if text:
            result.append(
                clean(text)
            )

    if not result:
        return (
            "आज कोई प्रमुख ग्रह राशि परिवर्तन नहीं हुआ है।"
        )

    return " ".join(
        result
    )


# ============================================================
# SELECT IMPORTANT INFLUENCES
# ============================================================

def important_influences(summary):

    influences = summary.get(
        "influences",
        []
    )

    ranked = sorted(
        influences,
        key=lambda item: (
            abs(item.get("score", 0)),
            PLANET_PRIORITY.get(
                item.get("planet"),
                1
            )
        ),
        reverse=True
    )

    return ranked[:2]


# ============================================================
# RASHI OVERALL LABEL
# ============================================================

def rashi_label(score):

    if score >= 4:
        return "अनुकूल"

    if score <= -4:
        return "सावधानी"

    return "मिश्रित"


# ============================================================
# MAIN RASHI INTERPRETATION
# ============================================================

def rashi_narration(summary):

    rashi = summary.get(
        "rashi",
        "राशि"
    )

    score = summary.get(
        "score",
        0
    )

    influences = important_influences(
        summary
    )

    lines = []

    lines.append(
        f"{rashi} राशि के लिए आज का गोचर "
        f"{rashi_label(score)} संकेत दे रहा है।"
    )

    # --------------------------------------------------------
    # TWO MOST IMPORTANT PLANETS
    # --------------------------------------------------------

    for item in influences:

        planet = item.get(
            "planet"
        )

        house = item.get(
            "house",
            1
        )

        score_value = item.get(
            "score",
            0
        )

        name = planet_name(
            planet
        )

        meaning = HOUSE_MEANING.get(
            house,
            "जीवन के महत्वपूर्ण विषय"
        )

        theme = PLANET_THEME.get(
            planet,
            "ग्रह संबंधी विषय"
        )

        if score_value > 0:

            sentence = (
                f"{name} {ordinal_house(house)} भाव में "
                f"होने से {meaning} से जुड़े मामलों में "
                f"{theme} को बल मिल सकता है।"
            )

        else:

            sentence = (
                f"{name} {ordinal_house(house)} भाव में "
                f"होने से {meaning} से जुड़े मामलों में "
                f"धैर्य और सावधानी जरूरी रहेगी।"
            )

        # Retrograde.
        if (
            getattr(
                item,
                "retrograde",
                False
            )
            and planet not in {
                "Rahu",
                "Ketu"
            }
        ):
            sentence += (
                " वक्री गति के कारण पुराने मामलों की "
                "पुनर्समीक्षा भी हो सकती है।"
            )

        lines.append(
            sentence
        )

    # --------------------------------------------------------
    # PRACTICAL ADVICE
    # --------------------------------------------------------

    if score >= 4:

        lines.append(
            "करियर और धन में अवसरों का लाभ लें, "
            "लेकिन जल्दबाजी से बचें। रिश्तों में "
            "सकारात्मक संवाद बनाए रखें।"
        )

    elif score <= -4:

        lines.append(
            "करियर और धन के मामलों में जोखिम से बचें। "
            "रिश्तों में धैर्य रखें और स्वास्थ्य के लिए "
            "आराम तथा नियमित दिनचर्या पर ध्यान दें।"
        )

    else:

        lines.append(
            "करियर और धन में संतुलित निर्णय लें। "
            "रिश्तों में स्पष्ट संवाद रखें और "
            "स्वास्थ्य के लिए नियमित दिनचर्या बनाए रखें।"
        )

    return " ".join(
        lines
    )


# ============================================================
# DAILY SCRIPT
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
        "नमस्कार! स्वागत है आपके दैनिक वैदिक "
        "ज्योतिष अपडेट में।"
    )

    lines.append(
        "आज चंद्र राशि के आधार पर जानते हैं "
        "बारह राशियों के लिए ग्रह गोचर के प्रमुख संकेत।"
    )

    # ========================================================
    # DATE
    # ========================================================

    if isinstance(
        date,
        datetime
    ):
        today = date.strftime(
            "%d-%m-%Y"
        )
    else:
        today = str(
            date
        )

    lines.append(
        f"आज की तारीख है {today}।"
    )

    # ========================================================
    # IMPORTANT PLANETS ONLY
    # ========================================================

    lines.append(
        "आज की प्रमुख ग्रह स्थिति इस प्रकार है।"
    )

    # Only show the slow / important planets in narration.
    important_order = [
        "Jupiter",
        "Saturn",
        "Rahu",
        "Ketu",
        "Mars",
        "Sun",
        "Mercury",
        "Venus",
        "Moon",
    ]

    position_map = {
        position.planet: position
        for position in positions
    }

    for planet in important_order:

        position = position_map.get(
            planet
        )

        if position is not None:

            lines.append(
                format_position(
                    position
                )
            )

    # ========================================================
    # TRANSITIONS
    # ========================================================

    lines.append(
        "आज के महत्वपूर्ण ग्रह परिवर्तन।"
    )

    lines.append(
        format_events(
            events
        )
    )

    # ========================================================
    # RASHI ANALYSIS
    # ========================================================

    lines.append(
        "अब जानते हैं बारह राशियों पर "
        "इन गोचर का प्रभाव।"
    )

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
    # 12 RASHIS
    # ========================================================

    for summary in summaries:

        lines.append(
            rashi_narration(
                summary
            )
        )

    # ========================================================
    # BEST / CAUTION
    # ========================================================

    ranked = sorted(
        summaries,
        key=lambda item: item.get(
            "score",
            0
        ),
        reverse=True
    )

    best = [
        item["rashi"]
        for item in ranked
        if item.get(
            "score",
            0
        ) >= 4
    ][:3]

    caution = [
        item["rashi"]
        for item in reversed(ranked)
        if item.get(
            "score",
            0
        ) <= -4
    ][:3]

    if best:

        lines.append(
            "आज अपेक्षाकृत अनुकूल संकेत "
            + ", ".join(best)
            + " राशि के लिए दिखाई दे रहे हैं।"
        )

    if caution:

        lines.append(
            "वहीं "
            + ", ".join(caution)
            + " राशि वालों को आज "
            "सावधानी और धैर्य रखने की सलाह है।"
        )

    # ========================================================
    # DISCLAIMER
    # ========================================================

    lines.append(
        "यह सामान्य चंद्र राशि आधारित दैनिक गोचर "
        "विश्लेषण है। व्यक्तिगत फलादेश के लिए "
        "जन्म कुंडली और दशा का अध्ययन आवश्यक होता है।"
    )

    # ========================================================
    # CTA
    # ========================================================

    lines.append(
        "अगर यह दैनिक वैदिक ज्योतिष अपडेट उपयोगी लगा "
        "तो चैनल को सब्सक्राइब करें और वीडियो को लाइक करें।"
    )

    lines.append(
        "कल फिर मिलेंगे नए ग्रह गोचर और नई राशिफल "
        "जानकारी के साथ। नमस्कार!"
    )

    return "\n".join(
        lines
    )
