from astro_engine.rules import SIGN_HI, interpret_for_rashi

def build_daily_script(date, positions, events):
    lines = [
        "नमस्कार! स्वागत है आज के ग्रह परिवर्तन अपडेट में।",
        "आज हम जल्दी से देखेंगे कि आकाश में कौन-कौन से महत्वपूर्ण परिवर्तन हैं और उनका बारहों राशियों पर क्या प्रभाव पड़ सकता है।"
    ]
    if events:
        lines.append("आज के प्रमुख ग्रह परिवर्तन:")
        for e in events[:5]:
            lines.append(f"• {e.description_hi}")
    else:
        lines.append("आज कोई बड़ा राशि परिवर्तन दर्ज नहीं हुआ है, लेकिन वर्तमान ग्रह स्थितियों के आधार पर दिन के प्रमुख संकेत देखते हैं।")

    lines.append("अब जानते हैं बारहों राशियों पर इसका संक्षिप्त प्रभाव।")
    for i, sign in enumerate(SIGN_HI):
        relevant = [interpret_for_rashi(p.planet, p.sign_index, i) for p in positions]
        lines.append(f"{sign} राशि: {' '.join(relevant[:2])}")

    lines.extend([
        "कुल मिलाकर आज सबसे महत्वपूर्ण संकेत ऊपर बताए गए ग्रह परिवर्तनों से जुड़े हैं।",
        "यह ज्योतिषीय व्याख्या है, निश्चित भविष्यवाणी नहीं। महत्वपूर्ण जीवन संबंधी निर्णय केवल इस वीडियो के आधार पर न लें।",
        "आपकी राशि कौन सी है? कमेंट में अपनी राशि लिखें और ऐसे दैनिक ग्रह अपडेट के लिए चैनल को सब्सक्राइब करें।"
    ])
    return "\n".join(lines)
