"""
Hindi daily horoscope content engine.

Reference:
    Chandra Rashi / Moon-sign based daily gochara.

Method:
    Nirayana / sidereal planetary positions
    + Lahiri ayanamsha
    + classical graha gochara
    + classical graha drishti
    + retrograde modifiers
    + sign-change events

The output is designed for approximately
3–5 minutes of Hindi narration.
"""

from datetime import datetime

from astro_engine.rules import (
    SIGN_HI,
    PLANET_HI,
    HOUSE_THEMES,
    relative_house,
    rashi_summary,
)


# ============================================================
# PLANET IMPORTANCE
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
# GENERAL HELPERS
# ============================================================

def planet_name(planet):
    return PLANET_HI.get(
        planet,
        planet
    )


def date_text(value):
    if isinstance(value, datetime):
        return value.strftime(
            "%d-%m-%Y"
        )

    return str(value)


def clean_text(text):
    """
    Remove accidental duplicated punctuation.
    """

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
# PLANETARY POSITIONS
# ============================================================

def format_position(position):

    name = planet_name(
        position.planet
    )

    sign = SIGN_HI[
        position.sign_index
    ]

    retrograde = ""

    if (
        position.retrograde
        and position.planet not in {
            "Rahu",
            "Ketu"
        }
    ):
        retrograde = " वक्री"

    return (
        f"{name} {sign राशि में "
        f"{position.longitude:.2f} डिग्री"
        f"{retrograde}"
    )


# ============================================================
# TRANSIT EVENTS
# ============================================================

def event_lines(events):

    if not events:
        return [
            "आज कोई प्रमुख ग्रह राशि परिवर्तन दर्ज नहीं हुआ है।"
        ]

    lines = []

    for event in events[:4]:

        description = clean_text(
            event.description_hi
        )

        lines.append(
            description
        )

    return lines


# ============================================================
# RASHI SCORE LABEL
# ============================================================

def rashi_label(score):

    if score >= 5:
        return "आज का गोचर अपेक्षाकृत अनुकूल है"

    if score <= -5:
        return "आज धैर्य और सावधानी की आवश्यकता है"

    return "आज का गोचर मिश्रित संकेत दे रहा है"


# ============================================================
# CATEGORY INTERPRETATION
# ============================================================

def category_advice(summary):

    influences = summary[
        "influences"
    ]

    positive = [
        item
        for item in influences
        if item["score"] > 0
    ]

    challenging = [
        item
        for item in influences
        if item["score"] < 0
    ]

    # --------------------------------------------------------
    # Career
    # --------------------------------------------------------

    career_houses = {
        3,
        6,
        10,
        11
    }

    career_items = [
        item
        for item in influences
        if item["house"] in career_houses
    ]

    if career_items:
        best = max(
            career_items,
            key=lambda item: item["score"]
        )

        if best["score"] > 0:
            career = (
                f"करियर में {planet_name(best['planet'])} "
                "के गोचर से प्रयासों और काम को आगे बढ़ाने "
                "का अवसर मिल सकता है।"
            )
        else:
            career = (
                "करियर में जल्दबाजी से बचें और लंबित "
                "जिम्मेदारियों को प्राथमिकता से पूरा करें।"
            )
    else:
        career = (
            "करियर में स्थिरता बनाए रखने और नियमित "
            "प्रयास जारी रखने का दिन है।"
        )

    # --------------------------------------------------------
    # Finance
    # --------------------------------------------------------

    finance_houses = {
        2,
        8,
        11,
        12
    }

    finance_items = [
        item
        for item in influences
        if item["house"] in finance_houses
    ]

    if finance_items:
        strongest = max(
            finance_items,
            key=lambda item: item["score"]
        )

        if strongest["score"] > 0:
            finance = (
                "धन संबंधी मामलों में अवसर दिखाई दे सकते हैं, "
                "लेकिन लाभ को स्थायी बनाने के लिए योजना जरूरी रहेगी।"
            )
        else:
            finance = (
                "धन के मामले में अनावश्यक खर्च और जोखिम "
                "से बचना बेहतर रहेगा।"
            )
    else:
        finance = (
            "आज धन के मामले में संतुलित बजट बनाए रखना उचित रहेगा।"
        )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    relationship_houses = {
        5,
        7,
        12
    }

    relationship_items = [
        item
        for item in influences
        if item["house"] in relationship_houses
    ]

    if relationship_items:

        strongest = max(
            relationship_items,
            key=lambda item: item["score"]
        )

        if strongest["score"] > 0:
            relationship = (
                "रिश्तों में संवाद और सहयोग बढ़ाने का अच्छा "
                "अवसर मिल सकता है।"
            )
        else:
            relationship = (
                "रिश्तों में प्रतिक्रिया देने से पहले "
                "दूसरे पक्ष की बात समझना बेहतर रहेगा।"
            )

    else:
        relationship = (
            "रिश्तों में सामान्य स्थिरता बनाए रखने के लिए "
            "स्पष्ट संवाद उपयोगी रहेगा।"
        )

    # --------------------------------------------------------
    # Health
    # --------------------------------------------------------

    health_houses = {
        1,
        6,
        8,
        12
    }

    health_items = [
        item
        for item in influences
        if item["house"] in health_houses
    ]

    if health_items:

        weakest = min(
            health_items,
            key=lambda item: item["score"]
        )

        if weakest["score"] < 0:
            health = (
                "स्वास्थ्य के लिए नियमित दिनचर्या, पर्याप्त "
                "आराम और तनाव को नियंत्रित करना उपयोगी रहेगा।"
            )
        else:
            health = (
                "स्वास्थ्य के मामले में नियमित दिनचर्या "
                "बनाए रखना लाभदायक रहेगा।"
            )

    else:
        health = (
            "स्वास्थ्य के लिए पर्याप्त नींद, संतुलित भोजन "
            "और नियमित दिनचर्या पर ध्यान दें।"
        )

    return {
        "career": career,
        "finance": finance,
        "relationship": relationship,
        "health": health,
    }


# ============================================================
# RASHI SCRIPT
# ============================================================

def build_rashi_section(summary):

    rashi = summary[
        "rashi"
    ]

    score = summary[
        "score"
    ]

    lines = []

    lines.append(
        f"{rashi} राशि"
    )

    lines.append(
        rashi_label(score) + "।"
    )

    # Select the most meaningful influences.
    influences = sorted(
        summary["influences"],
        key=lambda item: (
            abs(item["score"]),
            PLANET_PRIORITY.get(
                item["planet"],
                1
            )
        ),
        reverse=True
    )

    selected = influences[:3]

    for item in selected:

        text = clean_text(
            item["text"]
        )

        if text:
            lines.append(
                text
            )

    categories = category_advice(
        summary
    )

    lines.append(
        "करियर: " +
        categories["career"]
    )

    lines.append(
        "धन: " +
        categories["finance"]
    )

    lines.append(
        "रिश्ते: " +
        categories["relationship"]
    )

    lines.append(
        "स्वास्थ्य: " +
        categories["health"]
    )

    # Daily advice.
    if score >= 5:

        advice = (
            "आज मिले अवसरों का उपयोग करें, लेकिन "
            "अति-आत्मविश्वास से बचें।"
        )

    elif score <= -5:

        advice = (
            "आज बड़े निर्णयों में धैर्य रखें और "
            "अनावश्यक जोखिम से बचें।"
        )

    else:

        advice = (
            "आज संतुलित दृष्टिकोण रखें और महत्वपूर्ण "
            "निर्णय सोच-समझकर लें।"
        )

    lines.append(
        "आज की सलाह: " +
        advice
    )

    return lines


# ============================================================
# MAIN SCRIPT BUILDER
# ============================================================

def build_daily_script(
    date,
    positions,
    events
):

    lines = []

    # --------------------------------------------------------
    # INTRO
    # --------------------------------------------------------

    lines.append(
        "नमस्कार! स्वागत है आपके आज के दैनिक "
        "वैदिक ज्योतिष अपडेट में।"
    )

    lines.append(
        "आज हम चंद्र राशि के आधार पर बारह राशियों "
        "के लिए वर्तमान ग्रह गोचर का संक्षिप्त "
        "विश्लेषण करेंगे।"
    )

    lines.append(
        f"आज की तारीख है {date_text(date)}।"
    )

    # --------------------------------------------------------
    # CURRENT PLANETS
    # --------------------------------------------------------

    lines.append(
        "सबसे पहले जानते हैं वर्तमान ग्रह स्थिति।"
    )

    for position in positions:

        lines.append(
            format_position(
                position
            )
        )

    # --------------------------------------------------------
    # TRANSIT EVENTS
    # --------------------------------------------------------

    lines.append(
        "आज के महत्वपूर्ण ग्रह परिवर्तन।"
    )

    lines.extend(
        event_lines(events)
    )

    # --------------------------------------------------------
    # RASHI ANALYSIS
    # --------------------------------------------------------

    lines.append(
        "अब जानते हैं बारह राशियों पर इन गोचर का प्रभाव।"
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

    # --------------------------------------------------------
    # ALL RASHIS
    # --------------------------------------------------------

    for summary in summaries:

        lines.extend(
            build_rashi_section(
                summary
            )
        )

        lines.append(
            ""
        )

    # --------------------------------------------------------
    # OVERALL TREND
    # --------------------------------------------------------

    ranked = sorted(
        summaries,
        key=lambda item: item["score"],
        reverse=True
    )

    favourable = [
        item["rashi"]
        for item in ranked
        if item["score"] >= 5
    ][:3]

    cautious = [
        item["rashi"]
        for item in reversed(ranked)
        if item["score"] <= -5
    ][:3]

    if favourable:

        lines.append(
            "आज अपेक्षाकृत अनुकूल संकेत "
            + ", ".join(favourable)
            + " राशि के लिए दिखाई दे रहे हैं।"
        )

    if cautious:

        lines.append(
            "वहीं "
            + ", ".join(cautious)
            + " राशि वालों को आज विशेष धैर्य और "
            "सावधानी रखने की सलाह दी जाती है।"
        )

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------

    lines.append(
        "ध्यान रखें, यह विश्लेषण सामान्य चंद्र राशि "
        "आधारित दैनिक गोचर पर आधारित है। व्यक्तिगत "
        "फलादेश के लिए जन्म तिथि, जन्म समय, जन्म स्थान "
        "और पूरी जन्म कुंडली का अध्ययन आवश्यक होता है।"
    )

    lines.append(
        "इन संकेतों को पारंपरिक वैदिक ज्योतिष के "
        "मार्गदर्शन के रूप में देखें, निश्चित भविष्यवाणी "
        "के रूप में नहीं।"
    )

    # --------------------------------------------------------
    # CTA
    # --------------------------------------------------------

    lines.append(
        "अगर आपको यह दैनिक वैदिक ज्योतिष अपडेट उपयोगी "
        "लगा हो तो चैनल को सब्सक्राइब करें और वीडियो "
        "को लाइक करें।"
    )

    lines.append(
        "कल फिर मिलेंगे नए ग्रह गोचर और आपकी राशि के "
        "नए संकेतों के साथ। नमस्कार!"
    )

    return "\n".join(lines)
