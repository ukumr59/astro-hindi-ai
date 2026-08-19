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
# HELPER FUNCTIONS
# ============================================================

def planet_name(planet):
    """
    Convert internal planet name to Hindi.
    """

    return PLANET_HI.get(
        planet,
        planet
    )


def format_position(position):
    """
    Convert a planetary position into natural Hindi.
    """

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
            "Ketu",
        }
    ):
        retrograde = " (वक्री)"

    return (
        f"{name} {sign} राशि में "
        f"{position.longitude:.2f}°"
        f"{retrograde}"
    )


def event_lines(events):
    """
    Convert detected planetary sign-change events
    into concise Hindi narration.
    """

    if not events:
        return [
            "आज कोई प्रमुख ग्रह राशि परिवर्तन दर्ज नहीं हुआ है।"
        ]

    lines = []

    for event in events[:4]:

        description = getattr(
            event,
            "description_hi",
            ""
        )

        if description:
            lines.append(
                description.strip()
            )

    if not lines:
        lines.append(
            "आज कोई प्रमुख ग्रह राशि परिवर्तन दर्ज नहीं हुआ है।"
        )

    return lines


def importance_score(item):
    """
    Ranking helper for planetary influences.
    """

    score = item.get(
        "score",
        0
    )

    planet = item.get(
        "planet",
        ""
    )

    priority = PLANET_PRIORITY.get(
        planet,
        1
    )

    return (
        abs(score),
        priority
    )


def overall_rashi_label(score):
    """
    Convert numerical Vedic transit score
    into a viewer-friendly Hindi label.
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

    text = influence.get(
        "text",
        ""
    )

    if not text:
        return ""

    sentences = text.split(
        "।"
    )

    sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]

    if len(sentences) > 2:
        sentences = sentences[:2]

    return (
        "। ".join(sentences)
        + "।"
    )


# ============================================================
# RASHI-SPECIFIC CATEGORY ADVICE
# ============================================================

def category_advice(summary):
    """
    Convert the strongest transit houses into
    simple daily categories.

    This remains a general Chandra-Rashi reading,
    not a personal birth-chart prediction.
    """

    influences = summary.get(
        "influences",
        []
    )

    # --------------------------------------------------------
    # CAREER
    # --------------------------------------------------------

    career_houses = {
        3,
        6,
        10,
        11,
    }

    career_items = [
        item
        for item in influences
        if item.get("house") in career_houses
    ]

    if career_items:

        best = max(
            career_items,
            key=lambda item: item.get(
                "score",
                0
            )
        )

        if best.get(
            "score",
            0
        ) > 0:

            career = (
                f"करियर में {planet_name(best.get('planet'))} "
                "के गोचर से प्रयासों, जिम्मेदारियों और "
                "काम को आगे बढ़ाने के अवसर मिल सकते हैं।"
            )

        else:

            career = (
                "करियर में जल्दबाजी से बचें और लंबित "
                "जिम्मेदारियों को प्राथमिकता से पूरा करें।"
            )

    else:

        career = (
            "करियर में नियमित प्रयास और अनुशासन "
            "बनाए रखना उपयोगी रहेगा।"
        )

    # --------------------------------------------------------
    # FINANCE
    # --------------------------------------------------------

    finance_houses = {
        2,
        8,
        11,
        12,
    }

    finance_items = [
        item
        for item in influences
        if item.get("house") in finance_houses
    ]

    if finance_items:

        strongest = max(
            finance_items,
            key=lambda item: item.get(
                "score",
                0
            )
        )

        if strongest.get(
            "score",
            0
        ) > 0:

            finance = (
                "धन संबंधी मामलों में अवसर दिखाई दे सकते हैं। "
                "लाभ को स्थायी बनाने के लिए योजना और "
                "संतुलित खर्च जरूरी रहेगा।"
            )

        else:

            finance = (
                "धन के मामले में अनावश्यक खर्च, उधार और "
                "जोखिमपूर्ण निर्णयों से बचना बेहतर रहेगा।"
            )

    else:

        finance = (
            "आज धन के मामले में संतुलित बजट बनाए रखना "
            "उचित रहेगा।"
        )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    relationship_houses = {
        5,
        7,
        12,
    }

    relationship_items = [
        item
        for item in influences
        if item.get("house") in relationship_houses
    ]

    if relationship_items:

        strongest = max(
            relationship_items,
            key=lambda item: item.get(
                "score",
                0
            )
        )

        if strongest.get(
            "score",
            0
        ) > 0:

            relationship = (
                "रिश्तों में संवाद, सहयोग और "
                "आपसी समझ बढ़ाने का अच्छा अवसर मिल सकता है।"
            )

        else:

            relationship = (
                "रिश्तों में प्रतिक्रिया देने से पहले "
                "दूसरे पक्ष की बात समझना बेहतर रहेगा।"
            )

    else:

        relationship = (
            "रिश्तों में स्पष्ट संवाद और "
            "आपसी सम्मान बनाए रखना उपयोगी रहेगा।"
        )

    # --------------------------------------------------------
    # HEALTH
    # --------------------------------------------------------

    health_houses = {
        1,
        6,
        8,
        12,
    }

    health_items = [
        item
        for item in influences
        if item.get("house") in health_houses
    ]

    if health_items:

        weakest = min(
            health_items,
            key=lambda item: item.get(
                "score",
                0
            )
        )

        if weakest.get(
            "score",
            0
        ) < 0:

            health = (
                "स्वास्थ्य के लिए नियमित दिनचर्या, "
                "पर्याप्त आराम और तनाव को नियंत्रित "
                "करना उपयोगी रहेगा।"
            )

        else:

            health = (
                "स्वास्थ्य के मामले में नियमित दिनचर्या, "
                "संतुलित भोजन और पर्याप्त आराम लाभदायक रहेगा।"
            )

    else:

        health = (
            "स्वास्थ्य के लिए पर्याप्त नींद, "
            "संतुलित भोजन और नियमित दिनचर्या पर ध्यान दें।"
        )

    return {
        "career": career,
        "finance": finance,
        "relationship": relationship,
        "health": health,
    }


# ============================================================
# RASHI SECTION
# ============================================================

def build_rashi_section(summary):
    """
    Build the narration section for one Rashi.
    """

    lines = []

    rashi = summary.get(
        "rashi",
        "राशि"
    )

    score = summary.get(
        "score",
        0
    )

    label = overall_rashi_label(
        score
    )

    # --------------------------------------------------------
    # RASHI HEADING
    # --------------------------------------------------------

    lines.append(
        f"{rashi} राशि — {label}।"
    )

    # --------------------------------------------------------
    # STRONGEST PLANETARY INFLUENCES
    # --------------------------------------------------------

    influences = sorted(
        summary.get(
            "influences",
            []
        ),
        key=importance_score,
        reverse=True
    )

    selected = influences[:2]

    for influence in selected:

        text = short_influence_text(
            influence
        )

        if text:
            lines.append(
                text
            )

    # --------------------------------------------------------
    # CATEGORY ADVICE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DAILY ADVICE
    # --------------------------------------------------------

    if score >= 4:

        advice = (
            "आज मिले अवसरों का उपयोग करें, "
            "लेकिन अति-आत्मविश्वास से बचें।"
        )

    elif score <= -4:

        advice = (
            "आज बड़े निर्णयों में धैर्य रखें "
            "और अनावश्यक जोखिम से बचें।"
        )

    else:

        advice = (
            "आज संतुलित दृष्टिकोण रखें और "
            "महत्वपूर्ण निर्णय सोच-समझकर लें।"
        )

    lines.append(
        "आज की सलाह: " +
        advice
    )

    return lines


# ============================================================
# DAILY SCRIPT
# ============================================================

def build_daily_script(
    date,
    positions,
    events
):
    """
    Build the complete Hindi daily astrology script.

    The resulting script is designed to be consumed by
    the future video engine and Hindi voice engine.
    """

    lines = []

    # ========================================================
    # INTRO
    # ========================================================

    lines.append(
        "नमस्कार! स्वागत है आपके आज के दैनिक "
        "वैदिक ज्योतिष अपडेट में।"
    )

    lines.append(
        "आज हम देखेंगे वर्तमान ग्रह स्थिति, "
        "महत्वपूर्ण गोचर और चंद्र राशि के आधार पर "
        "सभी बारह राशियों पर उनके संभावित प्रभाव।"
    )

    # ========================================================
    # DATE
    # ========================================================

    if isinstance(
        date,
        datetime
    ):

        date_text = date.strftime(
            "%d-%m-%Y"
        )

    else:

        date_text = str(
            date
        )

    lines.append(
        f"आज की तारीख है {date_text}।"
    )

    # ========================================================
    # PLANETARY POSITIONS
    # ========================================================

    lines.append(
        "सबसे पहले जानते हैं वर्तमान ग्रह स्थिति।"
    )

    for position in positions:

        lines.append(
            format_position(
                position
            )
        )

    # ========================================================
    # IMPORTANT TRANSITIONS
    # ========================================================

    lines.append(
        "अब बात करते हैं आज के महत्वपूर्ण "
        "ग्रह परिवर्तनों की।"
    )

    lines.extend(
        event_lines(
            events
        )
    )

    # ========================================================
    # RASHI ANALYSIS
    # ========================================================

    lines.append(
        "अब शुरू करते हैं बारह राशियों का "
        "संक्षिप्त वैदिक गोचर विश्लेषण।"
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

    # ========================================================
    # RANK RASHIS
    # ========================================================

    positive_rashis = sorted(
        rashi_results,
        key=lambda item: item.get(
            "score",
            0
        ),
        reverse=True
    )

    cautious_rashis = sorted(
        rashi_results,
        key=lambda item: item.get(
            "score",
            0
        )
    )

    # ========================================================
    # ALL 12 RASHIS
    # ========================================================

    for summary in rashi_results:

        lines.extend(
            build_rashi_section(
                summary
            )
        )

        lines.append(
            ""
        )

    # ========================================================
    # BEST RASHIS
    # ========================================================

    best = [
        item["rashi"]
        for item in positive_rashis[:3]
        if item.get(
            "score",
            0
        ) > 0
    ]

    if best:

        lines.append(
            "आज के गोचर में अपेक्षाकृत बेहतर "
            "संकेत "
            + ", ".join(best)
            + " राशि के लिए दिखाई दे रहे हैं।"
        )

    # ========================================================
    # CAUTION RASHIS
    # ========================================================

    caution = [
        item["rashi"]
        for item in cautious_rashis[:3]
        if item.get(
            "score",
            0
        ) < 0
    ]

    if caution:

        lines.append(
            "वहीं "
            + ", ".join(caution)
            + " राशि वालों को आज जल्दबाजी से "
            "बचते हुए निर्णय लेने की सलाह है।"
        )

    # ========================================================
    # GENERAL ADVICE
    # ========================================================

    lines.append(
        "याद रखें, दैनिक गोचर सामान्य संकेत देता है। "
        "व्यक्तिगत फलादेश के लिए जन्म तिथि, जन्म समय, "
        "जन्म स्थान और पूरी जन्म कुंडली का अध्ययन "
        "आवश्यक होता है।"
    )

    # ========================================================
    # DISCLAIMER
    # ========================================================

    lines.append(
        "इन ज्योतिषीय संकेतों को निश्चित भविष्यवाणी "
        "के बजाय पारंपरिक वैदिक ज्योतिष के मार्गदर्शन "
        "के रूप में देखें।"
    )

    # ========================================================
    # CTA
    # ========================================================

    lines.append(
        "अगर आपको यह दैनिक वैदिक ज्योतिष अपडेट "
        "उपयोगी लगा, तो चैनल को सब्सक्राइब करें "
        "और वीडियो को लाइक करें।"
    )

    lines.append(
        "कल फिर मिलेंगे नए ग्रह गोचर और आपकी "
        "राशि के नए संकेतों के साथ। नमस्कार!"
    )

    return "\n".join(
        lines
    )
