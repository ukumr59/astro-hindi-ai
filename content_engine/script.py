"""Original, materially differentiated Hindi astrology script generation."""
from datetime import datetime
import re
from astro_engine.rules import rashi_summary
from .diversity import select_content_profile

PLANET_HI={"Sun":"सूर्य","Moon":"चंद्रमा","Mars":"मंगल","Mercury":"बुध","Jupiter":"गुरु","Venus":"शुक्र","Saturn":"शनि","Rahu":"राहु","Ketu":"केतु"}
HOUSE_THEMES={1:"व्यक्तित्व और आत्मविश्वास",2:"धन, बचत और परिवार",3:"साहस, प्रयास और संचार",4:"घर, संपत्ति और मानसिक सुख",5:"शिक्षा, रचनात्मकता और प्रेम",6:"काम, प्रतियोगिता और अनुशासन",7:"साझेदारी और सार्वजनिक संबंध",8:"परिवर्तन और साझा संसाधन",9:"भाग्य, गुरु और उच्च शिक्षा",10:"करियर, प्रतिष्ठा और जिम्मेदारी",11:"आय, लाभ और नेटवर्क",12:"व्यय, विश्राम और आत्मचिंतन"}
LENS=(("करियर","काम और जिम्मेदारी में आज किस संकेत को प्राथमिकता देनी है"),("धन","कमाई, बचत और खर्च में किस बात पर सजग रहना है"),("रिश्ते","संवाद और साझेदारी में किस व्यवहार से संतुलन बनेगा"),("निर्णय","आज किसी निर्णय को लेने से पहले किस संकेत को तौलना है"),("प्रयास","किस काम में निरंतरता और व्यावहारिक प्रयास सबसे उपयोगी रहेगा"),("सीख","अनुभव, अध्ययन और नई समझ से आज क्या हासिल किया जा सकता है"),("संतुलन","अवसर और सावधानी के बीच आज संतुलन कैसे रखा जाए"),("परिवर्तन","बदलती परिस्थितियों में किस बात को स्वीकार और किसे जांचना है"),("नेटवर्क","लोगों, सहयोग और संपर्कों से जुड़े संकेतों को कैसे उपयोगी बनाया जाए"),("अनुशासन","रूटीन, समय और लंबित काम को किस तरह व्यवस्थित करना है"),("आत्मचिंतन","आज के अनुभव से कौन-सी प्राथमिकता स्पष्ट हो सकती है"),("योजना","आज की ऊर्जा को अगले कदम की स्पष्ट योजना में कैसे बदला जाए"))

def date_text(value): return value.strftime("%d-%m-%Y") if isinstance(value,datetime) else str(value)
def clean(text): return " ".join((text or "").replace("।।","।").split()).strip()
def complete_sentences(text,limit=3):
    text=clean(text)
    if not text:return []
    parts=[clean(x) for x in re.split(r"(?<=[।!?])\s+",text) if clean(x)]
    return parts[:limit] if parts else [text]
def _ending(text): return text if text.endswith(("।","!","?")) else text+"।"
def _signal_text(item): return clean(" ".join(complete_sentences(item.get("text",""),2)))
def _ranked_signals(summary,count=4):
    items=list(summary.get("influences",[])); items.sort(key=lambda x:(abs(x.get("score",0)),x.get("score",0)),reverse=True)
    return [x for x in items if _signal_text(x)][:count]

def rashi_line(summary,style="signal",rashi_index=0):
    """Build a substantive section from multiple actual transit signals."""
    rashi=clean(summary.get("rashi","राशि")); overall=summary.get("overall","मिश्रित"); score=summary.get("score",0)
    signals=_ranked_signals(summary,4); lens,lens_question=LENS[rashi_index%len(LENS)]
    opening={"अनुकूल":"आज के संकेतों में आगे बढ़ने की गुंजाइश दिखती है, लेकिन प्राथमिकता स्पष्ट रखना जरूरी है","सावधानी":"आज के संकेत धैर्य, जांच और संतुलित गति को अधिक महत्व देते हैं","मिश्रित":"आज का संकेत एकतरफा नहीं है; कुछ क्षेत्रों में अवसर और कुछ में संयम साथ-साथ दिखता है"}.get(overall,"आज के संकेतों को संतुलित दृष्टि से देखना उपयोगी रहेगा")
    lines=[f"{rashi} राशि के लिए आज का विश्लेषण। {opening}।",f"ग्रह-संकेतों का संयुक्त स्कोर {score} है और आज का संपादकीय फोकस {lens} है—{lens_question}।"]
    if signals:
        lead=signals[0]; planet=PLANET_HI.get(lead.get("planet"),lead.get("planet","ग्रह")); house=lead.get("house"); theme=HOUSE_THEMES.get(house,"जीवन के महत्वपूर्ण विषय")
        lines.append(f"सबसे प्रमुख संकेत {planet} का है, जो {house}वें भाव से जुड़े {theme} पर ध्यान खींचता है। {_signal_text(lead)}")
    for item in signals[1:4]:
        planet=PLANET_HI.get(item.get("planet"),item.get("planet","ग्रह")); house=item.get("house"); theme=HOUSE_THEMES.get(house,"जीवन के महत्वपूर्ण विषय"); quality=item.get("score",0); direction="सहयोगी" if quality>0 else "सावधानी वाला" if quality<0 else "तटस्थ"
        lines.append(f"इसके साथ {planet} का {house}वें भाव वाला संकेत {theme} में {direction} रुख दिखाता है। {_signal_text(item)}")
    if overall=="अनुकूल": action=f"आज का व्यावहारिक कदम: {lens} से जुड़े एक महत्वपूर्ण काम को पहले पूरा करें और अच्छे संकेत को जल्दबाजी में जोखिम में न बदलें।"
    elif overall=="सावधानी": action=f"आज का व्यावहारिक कदम: {lens} में कोई बड़ा कदम लेने से पहले जानकारी, समय और संभावित परिणाम की दोबारा जांच करें।"
    else: action=f"आज का व्यावहारिक कदम: {lens} में अवसर को पहचानें, लेकिन निर्णय से पहले विरोधी संकेतों को भी तौलें।"
    lines.append(action)
    return " ".join(_ending(clean(x)) for x in lines if clean(x))

def _intro(date,profile):
    d=date_text(date); common=f"आज {d} को निरयन और लाहिरी पद्धति के आधार पर चंद्र राशियों के लिए ग्रह संकेत देखेंगे।"
    intros={"overview":["नमस्कार! आज के दैनिक वैदिक ज्योतिष अपडेट में आपका स्वागत है।",common,profile.hook],"opportunity":[f"नमस्कार! {d} के लिए अवसर, प्रगति और सावधानी के संकेतों को समझते हैं।",common,profile.hook],"caution":[f"नमस्कार! {d} के राशिफल में कहां आगे बढ़ना है और कहां संयम रखना है, जानते हैं।",common,profile.hook],"planet":[f"नमस्कार! आज के ग्रह संकेतों की कहानी से {d} का दैनिक राशिफल समझते हैं।",common,profile.hook],"practical":[f"नमस्कार! {d} के ग्रह संकेतों को आज के व्यावहारिक फैसलों से जोड़कर देखते हैं।",common,profile.hook],"focus":[f"नमस्कार! {d} के लिए आज के तीन बड़े फोकस से बारहों राशियों को समझते हैं।",common,profile.hook],"reflection":[f"नमस्कार! {d} की दिन-ऊर्जा को ग्रह संकेत और आत्मचिंतन के साथ समझते हैं।",common,profile.hook]}
    return intros[profile.intro_style]

def _event_lines(events,style):
    if not events:return ["आज कोई प्रमुख राशि परिवर्तन दर्ज नहीं हुआ है। इसलिए वर्तमान ग्रह स्थितियों और उनके संयुक्त प्रभाव के आधार पर दैनिक संकेत देखेंगे।"]
    desc=[_ending(clean(getattr(event,"description_hi",""))) for event in events[:3] if clean(getattr(event,"description_hi",""))]
    headers={"priority":"आज के प्रमुख ग्रह परिवर्तन, प्राथमिकता के क्रम में:","opportunity":"आज के ग्रह परिवर्तन अवसर और सावधानी के संकेत दे सकते हैं:","risk":"आज के ग्रह परिवर्तन को निर्णय लेते समय ध्यान में रखें:","story":"आज की ग्रह-कथा में ये प्रमुख परिवर्तन महत्वपूर्ण हैं:","action":"आज की योजना बनाते समय इन प्रमुख ग्रह परिवर्तनों को संदर्भ में रखें:","three_focus":"आज के तीन फोकस में सबसे पहले इन ग्रह संकेतों को समझें:","reflection":"आज की दिन-ऊर्जा को प्रभावित करने वाले प्रमुख ग्रह परिवर्तन:"}
    return [headers.get(style,headers["reflection"])] + desc

def _outro(profile):
    endings={"day_overview":"यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा का अध्ययन आवश्यक होता है। आज के संकेतों को अपनी परिस्थितियों के संदर्भ में समझें। कल फिर नए ग्रह संकेतों के साथ मिलेंगे। नमस्कार!","opportunity_map":"यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। अवसर का लाभ लेने से पहले अपनी परिस्थितियों को भी ध्यान में रखें। कल फिर नई ग्रह दिशा के साथ मिलेंगे। नमस्कार!","caution_balance":"यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। आज के संकेत अंतिम निर्णय नहीं, बल्कि सजगता और संतुलन का संदर्भ हैं। कल फिर मिलेंगे। नमस्कार!","planet_story":"यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। ग्रह संकेत व्यापक प्रवृत्तियां बताते हैं; व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा आवश्यक हैं। नमस्कार!","practical_guide":"यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। संकेतों को अपने वास्तविक निर्णयों के साथ सोच-समझकर जोड़ें। कल फिर मिलेंगे। नमस्कार!","focus_three":"यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। अवसर, सावधानी और संतुलन को अपनी परिस्थितियों के अनुसार देखें। कल नए फोकस के साथ मिलेंगे। नमस्कार!","reflection":"यह सामान्य चंद्र राशि आधारित गोचर विश्लेषण है। आज के संकेतों को आत्मचिंतन, व्यवहार और वास्तविक परिस्थितियों के साथ जोड़ें। कल फिर नई दिन-ऊर्जा के साथ मिलेंगे। नमस्कार!"}
    return endings[profile.key]

def build_daily_script(date,positions,events):
    profile=select_content_profile(date); lines=_intro(date,profile); lines.extend(_event_lines(events,profile.event_style))
    transitions={"day_overview":"अब बारहों राशियों के लिए अलग-अलग ग्रह संकेत देखते हैं।","opportunity_map":"अब हर राशि के लिए अवसर और सावधानी के वास्तविक ग्रह-आधार को समझते हैं।","caution_balance":"अब प्रत्येक राशि के संकेतों में जोखिम, धैर्य और संतुलन के अलग कारण देखते हैं।","planet_story":"अब ग्रह संकेतों को एक-एक राशि के अलग भाव-संदर्भ से समझते हैं।","practical_guide":"अब हर राशि के संकेत के साथ अलग व्यावहारिक दिशा देखते हैं।","focus_three":"अब बारहों राशियों को उनके वास्तविक ग्रह-संकेत और तीन मुख्य फोकस के संदर्भ में समझते हैं।","reflection":"अब हर राशि के लिए ग्रह-संकेत, भाव और व्यवहारिक अर्थ को अलग-अलग देखते हैं।"}
    lines.append(transitions[profile.key])
    for i in range(12):lines.append(rashi_line(rashi_summary(i,positions),profile.rashi_style,i))
    lines.append(_outro(profile)); return "\n".join(lines)
