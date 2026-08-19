"""
Hindi daily content engine for Vedic / Jyotisha Gochar.

Flow:
    Real planetary positions
        ->
    Chandra Rashi based gochar
        ->
    Classical Vedic interpretation
        ->
    Hindi daily narration
"""

from datetime import datetime

from astro_engine.rules import (
    SIGN_HI,
    rashi_summary,
)


# ============================================================
# HELPERS
# ============================================================

def get_date_text(date):
    if isinstance(date, datetime):
        return date.strftime("%d-%m-%Y")

    return str(date)


def get_top_influences(summary, limit=2):
    influences = summary.get(
        "influences",
        []
    )

    # Prefer strongest classical influence.
    ranked = sorted(
        influences,
        key=lambda item: (
            abs(item.get("score", 0)),
            item.get("score", 0)
        ),
        reverse=True
    )

    return ranked[:limit]


def overall_text(summary):
    overall = summary.get(
        "overall",
        "मिश्रित"
    )

    if overall == "अनुकूल":
        return (
            "आज के गोचर से इस राशि के लिए "
            "कुल मिलाकर सकारात्मक संकेत बन रहे हैं।"
        )

    if overall == "सावधानी":
        return (
            "आज इस राशि को महत्वपूर्ण मामलों में "
            "सावधानी और धैर्य रखना बेहतर रहेगा।"
        )

    return (
        "आज इस राशि के लिए ग्रहों का प्रभाव "
        "मिश्रित है, इसलिए संतुलित निर्णय लेना बेहतर रहेगा।"
    )


def rashi_section(
    summary,
    index
):
    rashi = summary["rashi"]

    lines = []

    lines.append(
        f"{rashi} राशि:"
    )

    lines.append(
        overall_text(
            summary
        )
    )

    influences = get_top_influences(
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
                text
            )

    # Practical guidance.
    score = summary.get(
        "score",
        0
    )

    if score >= 5:

        lines.append(
            "करियर और धन से जुड़े अवसरों का "
            "समझदारी से लाभ उठाएं और सकारात्मक "
            "प्रयास जारी रखें।"
        )

    elif score <= -5:

        lines.append(
            "आज बड़े जोखिम और जल्दबाजी से बचें। "
            "धन, करियर और रिश्तों में सोच-समझकर "
            "निर्णय लेना बेहतर रहेगा।"
        )

    else:

        lines.append(
            "आज संतुलित दृष्टिकोण रखें और "
            "महत्वपूर्ण निर्णय सोच-समझकर लें।"
        )

    return " ".join(
        lines
    )


# ============================================================
# MAIN SCRIPT BUILDER
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
        "आज हम निरयन राशि और चंद्र राशि के आधार पर "
        "ग्रह गोचर के प्रमुख प्रभाव जानेंगे।"
    )

    lines.append(
        f"आज की तारीख है {get_date_text(date)}।"
    )

    # ========================================================
    # TRANSIT EVENTS
    # ========================================================

    lines.append(
        "आज के प्रमुख ग्रह परिवर्तन:"
    )

    if events:

        for event in events[:5]:

            description = getattr(
                event,
                "description_hi",
                ""
            )

            if description:
                lines.append(
                    description
                )

    else:

        lines.append(
            "आज कोई प्रमुख राशि परिवर्तन दर्ज नहीं हुआ है। "
            "इसलिए वर्तमान ग्रह स्थितियों के आधार पर "
            "दैनिक गोचर के संकेत देखेंगे।"
        )

    # ========================================================
    # RASHI ANALYSIS
    # ========================================================

    lines.append(
        "अब जानते हैं बारहों चंद्र राशियों पर "
        "आज के ग्रह गोचर का प्रभाव।"
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
    # EACH RASHI
    # ========================================================

    for index, summary in enumerate(
        summaries
    ):

        lines.append(
            rashi_section(
                summary,
                index
            )
        )

    # ========================================================
    # DAILY HIGHLIGHTS
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
        ) >= 5
    ][:3]

    caution = [
        item["rashi"]
        for item in reversed(ranked)
        if item.get(
            "score",
            0
        ) <= -5
    ][:3]

    if best:

        lines.append(
            "आज अपेक्षाकृत अनुकूल संकेत "
            + ", ".join(best)
            + " राशि के लिए दिखाई दे रहे हैं।"
        )

    if caution:

        lines.append(
            "सावधानी रखने वाली राशियों में "
            + ", ".join(caution)
            + " शामिल हैं।"
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
    # CTA
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
