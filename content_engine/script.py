"""Production-grade daily Hindi astrology script generation with editorial rotation."""
from datetime import datetime
import re
from astro_engine.rules import rashi_summary
from .diversity import select_content_profile


def date_text(value):
    return value.strftime("%d-%m-%Y") if isinstance(value, datetime) else str(value)


def clean(text):
    return " ".join((text or "").replace("।।", "।").split()).strip()


def complete_sentences(text, limit=2):
    text = clean(text)
    if not text:
        return []
    parts = [clean(x) for x in re.split(r"(?<=[।!?])\s+", text) if clean(x)]
    return parts[:limit] if parts else [text]


def strongest(summary):
    items = sorted(summary.get("influences", []), key=lambda x: abs(x.get("score", 0)), reverse=True)
    if not items:
        return ""
    return " ".join(complete_sentences(items[0].get("text", ""), limit=2))


def _ending(text):
    return text if text.endswith(("।", "!", "?")) else text + "।"


def rashi_line(summary, style="signal"):
    rashi = clean(summary.get("rashi", "राशि"))
    overall = summary.get("overall", "मिश्रित")
    influence = strongest(summary)
    base = {"अनुकूल": "आज का दिन कुल मिलाकर अनुकूल संकेत दे रहा है।", "सावधानी": "आज धैर्य और सावधानी के साथ आगे बढ़ना बेहतर रहेगा।"}.get(overall, "आज मिश्रित संकेत हैं; संतुलित निर्णय लेना बेहतर रहेगा।")
    advice = {"अनुकूल": "काम में अवसरों का लाभ लें और धन संबंधी निर्णय सोच-समझकर करें।", "सावधानी": "जल्दबाजी से बचें, खर्च नियंत्रित रखें और रिश्तों में संयम रखें।"}.get(overall, "काम, धन और रिश्तों में स्पष्ट संवाद तथा संतुलन रखें।")
    if style == "opportunity":
        pieces = [f"{rashi} राशि।", "आज अवसर और प्रगति की दिशा पर विशेष ध्यान दें।" if overall == "अनुकूल" else "आज अवसर चुनते समय जोखिम और समय दोनों का संतुलन जरूरी है।", influence, advice]
    elif style == "balance":
        pieces = [f"{rashi} राशि।", "आज संतुलन बनाए रखना सबसे महत्वपूर्ण संकेत है।", base, influence, advice]
    elif style == "cause_effect":
        pieces = [f"{rashi} राशि।", "ग्रहों के आज के संकेत आपके व्यवहार और निर्णयों पर असर डाल सकते हैं।", influence or base, advice]
    elif style == "practical":
        pieces = [f"{rashi} राशि।", base, "व्यावहारिक फोकस रखें—काम, धन और संवाद में एक-एक कदम सोचकर बढ़ाएं।", influence, advice]
    elif style == "focus":
        focus = "अवसर" if overall == "अनुकूल" else "सावधानी" if overall == "सावधानी" else "संतुलन"
        pieces = [f"{rashi} राशि।", f"आज का मुख्य फोकस: {focus}।", influence or base, advice]
    elif style == "reflection":
        pieces = [f"{rashi} राशि।", "आज के संकेतों को अपने व्यवहार और प्राथमिकताओं के साथ जोड़कर देखें।", influence or base, advice]
    else:
        pieces = [f"{rashi} राशि।", base, influence, advice]
    return " ".join(_ending(clean(x)) for x in pieces if clean(x))


def _intro(date, profile):
    d = date_text(date)
    common = f"आज {d} को निरयन और लाहिरी पद्धति के आधार पर चंद्र राशियों के लिए ग्रह संकेत देखेंगे।"
    intros = {
        "overview": ["नमस्कार! आज के दैनिक वैदिक ज्योतिष अपडेट में आपका स्वागत है।", common, profile.hook],
        "opportunity": [f"नमस्कार! {d} के लिए अवसर, प्रगति और सावधानी के संकेतों को समझते हैं।", common, profile.hook],
        "caution": [f"नमस्कार! {d} के राशिफल में कहां आगे बढ़ना है और कहां संयम रखना है, जानते हैं।", common, profile.hook],
        "planet": [f"नमस्कार! आज के ग्रह संकेतों की कहानी से {d} का दैनिक राशिफल समझते हैं।", common, profile.hook],
        "practical": [f"नमस्कार! {d} के ग्रह संकेतों को आज के व्यावहारिक फैसलों से जोड़कर देखते हैं।", common, profile.hook],
        "focus": [f"नमस्कार! {d} के लिए आज के तीन बड़े फोकस से बारहों राशियों को समझते हैं।", common, profile.hook],
        "reflection": [f"नमस्कार! {d} की दिन-ऊर्जा को ग्रह संकेत और आत्मचिंतन के साथ समझते हैं।", common, profile.hook],
    }
    return intros[profile.intro_style]


def _event_lines(events, style):
    if not events:
        return ["आज कोई प्रमुख राशि परिवर्तन दर्ज नहीं हुआ है। इसलिए वर्तमान ग्रह स्थितियों और उनके संयुक्त प्रभाव के आधार पर दैनिक संकेत देखेंगे।"]
    desc = [_ending(clean(getattr(event, "description_hi", ""))) for event in events[:3] if clean(getattr(event, "description_hi", ""))]
    headers = {"priority": "आज के प्रमुख ग्रह परिवर्तन, प्राथमिकता के क्रम में:", "opportunity": "आज के ग्रह परिवर्तन अवसर और सावधानी के संकेत दे सकते हैं:", "risk": "आज के ग्रह परिवर्तन को निर्णय लेते समय ध्यान में रखें:", "story": "आज की ग्रह-कथा में ये प्रमुख परिवर्तन महत्वपूर्ण हैं:", "action": "आज की योजना बनाते समय इन प्रमुख ग्रह परिवर्तनों को संदर्भ में रखें:", "three_focus": "आज के तीन फोकस में सबसे पहले इन ग्रह संकेतों को समझें:", "reflection": "आज की दिन-ऊर्जा को प्रभावित करने वाले प्रमुख ग्रह परिवर्तन:"}
    return [headers.get(style, headers["reflection"])] + desc


def _outro(profile):
    endings = {
        "day_overview": "यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा का अध्ययन आवश्यक होता है। आज के संकेत उपयोगी लगे तो अपनी राशि के साथ इस जानकारी को याद रखें। कल फिर नए ग्रह संकेतों के साथ मिलेंगे। नमस्कार!",
        "opportunity_map": "यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। अवसर का लाभ लेने से पहले अपनी व्यक्तिगत परिस्थितियों और जन्म कुंडली को भी ध्यान में रखें। कल फिर नई ग्रह दिशा के साथ मिलेंगे। नमस्कार!",
        "caution_balance": "यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। आज के संकेतों को अंतिम निर्णय नहीं, बल्कि सजगता और संतुलन के एक संदर्भ की तरह लें। कल फिर मिलेंगे। नमस्कार!",
        "planet_story": "यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। ग्रह संकेत व्यापक प्रवृत्तियां बताते हैं; व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा आवश्यक हैं। अगले ग्रह संकेतों के साथ फिर मिलेंगे। नमस्कार!",
        "practical_guide": "यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। आज का सबसे अच्छा उपयोग यही है कि संकेतों को अपने काम, धन और संबंधों के वास्तविक निर्णयों के साथ सोच-समझकर जोड़ें। कल फिर मिलेंगे। नमस्कार!",
        "focus_three": "यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। आज के अवसर, सावधानी और संतुलन—इन तीनों को अपनी परिस्थितियों के अनुसार देखें। कल नए फोकस के साथ मिलेंगे। नमस्कार!",
        "reflection": "यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। आज के संकेतों को आत्मचिंतन, व्यवहार और वास्तविक परिस्थितियों के साथ जोड़ना सबसे उपयोगी रहेगा। कल फिर नई दिन-ऊर्जा के साथ मिलेंगे। नमस्कार!",
    }
    return endings[profile.key]


def build_daily_script(date, positions, events):
    profile = select_content_profile(date)
    lines = _intro(date, profile)
    lines.extend(_event_lines(events, profile.event_style))
    transitions = {"day_overview": "अब बारहों राशियों के लिए आज के ग्रह संकेत देखते हैं।", "opportunity_map": "अब देखते हैं किस राशि के लिए आज अवसर, प्रगति या अतिरिक्त सावधानी का संकेत है।", "caution_balance": "अब प्रत्येक राशि के लिए जोखिम, धैर्य और संतुलन के संकेत समझते हैं।", "planet_story": "अब ग्रह संकेतों के प्रभाव को एक-एक राशि के संदर्भ में समझते हैं।", "practical_guide": "अब बारहों राशियों के लिए संकेत के साथ एक व्यावहारिक दिशा भी देखते हैं।", "focus_three": "अब अवसर, सावधानी और संतुलन के तीन फोकस के आधार पर राशियों को समझते हैं।", "reflection": "अब हर राशि के लिए दिन के संकेतों को व्यवहार और प्राथमिकताओं के संदर्भ में देखते हैं।"}
    lines.append(transitions[profile.key])
    for i in range(12):
        lines.append(rashi_line(rashi_summary(i, positions), profile.rashi_style))
    lines.append(_outro(profile))
    return "\n".join(lines)
