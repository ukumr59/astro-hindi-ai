"""Concise daily Hindi astrology script for social-first videos."""
from datetime import datetime
from astro_engine.rules import rashi_summary


def date_text(value):
    return value.strftime("%d-%m-%Y") if isinstance(value, datetime) else str(value)


def clean(text):
    return " ".join((text or "").replace("।।", "।").split())


def strongest(summary):
    items = sorted(summary.get("influences", []), key=lambda x: abs(x.get("score", 0)), reverse=True)
    return clean(items[0].get("text", "")) if items else ""


def rashi_line(summary):
    rashi = summary.get("rashi", "राशि")
    overall = summary.get("overall", "मिश्रित")
    lead = {
        "अनुकूल": "आज का दिन कुल मिलाकर अनुकूल संकेत दे रहा है।",
        "सावधानी": "आज धैर्य और सावधानी के साथ आगे बढ़ना बेहतर रहेगा।",
    }.get(overall, "आज मिश्रित संकेत हैं; संतुलित निर्णय लेना बेहतर रहेगा।")
    influence = strongest(summary)
    if influence:
        influence = " ".join(influence.split()[:28])
    advice = {
        "अनुकूल": "काम में अवसरों का लाभ लें और धन संबंधी निर्णय सोच-समझकर करें।",
        "सावधानी": "जल्दबाजी से बचें, खर्च नियंत्रित रखें और रिश्तों में संयम रखें।",
    }.get(overall, "काम, धन और रिश्तों में स्पष्ट संवाद तथा संतुलन रखें।")
    return f"{rashi} राशि। {lead} {influence} {advice}"


def build_daily_script(date, positions, events):
    lines = [
        "नमस्कार! स्वागत है आपके दैनिक वैदिक ज्योतिष अपडेट में।",
        f"आज {date_text(date)} को निरयन और लाहिरी पद्धति के आधार पर बारहों चंद्र राशियों के लिए प्रमुख गोचर संकेत जानेंगे।",
    ]
    if events:
        lines.append("आज के प्रमुख ग्रह परिवर्तन:")
        for event in events[:2]:
            desc = clean(getattr(event, "description_hi", ""))
            if desc:
                lines.append(desc)
    else:
        lines.append("आज कोई प्रमुख राशि परिवर्तन दर्ज नहीं हुआ है; इसलिए वर्तमान ग्रह स्थितियों के आधार पर दैनिक संकेत देखेंगे।")
    lines.append("अब जानते हैं बारहों राशियों पर आज के ग्रह गोचर का प्रभाव।")
    for i in range(12):
        lines.append(rashi_line(rashi_summary(i, positions)))
    lines.append("यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है; व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा का अध्ययन आवश्यक होता है।")
    lines.append("वीडियो उपयोगी लगे तो लाइक, फॉलो और सब्सक्राइब करें। कल फिर मिलेंगे नए ग्रह संकेतों के साथ। नमस्कार!")
    return "\n".join(lines)
