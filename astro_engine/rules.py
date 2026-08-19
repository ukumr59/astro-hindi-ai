"""
Vedic / Jyotisha transit rules.

Methodology used by this project:

1. Nirayana / sidereal zodiac
2. Lahiri ayanamsha for planetary positions
3. Chandra Rashi as the mass-horoscope reference
4. Transit house counted from Janma Chandra Rashi
5. Classical graha-specific gochara tendencies
6. Classical special drishti for Mars, Jupiter and Saturn
7. Rahu/Ketu treated as shadow planets
8. Retrograde status used as an interpretive modifier

Important:
This is a rule-based Jyotisha interpretation engine, not a
claim of scientific prediction. Different Jyotisha traditions
can use different rules, especially for Rahu/Ketu and aspects.
The conventions below are deliberately kept explicit and
consistent.
"""


# ============================================================
# HINDI NAMES
# ============================================================

PLANET_HI = {
    "Sun": "सूर्य",
    "Moon": "चंद्रमा",
    "Mars": "मंगल",
    "Mercury": "बुध",
    "Jupiter": "गुरु",
    "Venus": "शुक्र",
    "Saturn": "शनि",
    "Rahu": "राहु",
    "Ketu": "केतु",
}


SIGN_HI = [
    "मेष",
    "वृषभ",
    "मिथुन",
    "कर्क",
    "सिंह",
    "कन्या",
    "तुला",
    "वृश्चिक",
    "धनु",
    "मकर",
    "कुंभ",
    "मीन",
]


# ============================================================
# HOUSE THEMES
# ============================================================

HOUSE_THEMES = {
    1: "व्यक्तित्व, स्वास्थ्य, आत्मविश्वास और नई शुरुआत",
    2: "धन, बचत, परिवार और वाणी",
    3: "साहस, प्रयास, संचार और छोटे सफर",
    4: "घर, संपत्ति, माता और मानसिक सुख",
    5: "शिक्षा, बुद्धि, रचनात्मकता, प्रेम और संतान",
    6: "रोग, ऋण, प्रतियोगिता, नौकरी और दैनिक दिनचर्या",
    7: "विवाह, साझेदारी, संबंध और सार्वजनिक व्यवहार",
    8: "अचानक परिवर्तन, साझा धन, रहस्य और गहन विषय",
    9: "भाग्य, धर्म, गुरु, उच्च शिक्षा और लंबी यात्रा",
    10: "कर्म, करियर, प्रतिष्ठा और जिम्मेदारी",
    11: "आय, लाभ, इच्छापूर्ति और नेटवर्क",
    12: "व्यय, विश्राम, एकांत, विदेश और आध्यात्मिक चिंतन",
}


# ============================================================
# CLASSICAL GOCHARA TENDENCIES
# ============================================================
#
# Houses generally considered more supportive for each graha
# when counted from the natal Moon sign.
#
# These are intentionally stored as data rather than buried
# inside the interpretation function.
# ============================================================

FAVOURABLE_HOUSES = {

    "Sun": {
        3, 6, 10, 11
    },

    "Moon": {
        1, 3, 6, 7, 10, 11
    },

    "Mars": {
        3, 6, 11
    },

    "Mercury": {
        2, 4, 6, 8, 10, 11
    },

    "Jupiter": {
        2, 5, 7, 9, 11
    },

    "Venus": {
        1, 2, 3, 4, 5, 8, 9, 11, 12
    },

    "Saturn": {
        3, 6, 11
    },

    "Rahu": {
        3, 6, 10, 11
    },

    "Ketu": {
        3, 6, 10, 11
    },
}


# ============================================================
# GRAHA THEMES
# ============================================================

PLANET_THEMES = {

    "Sun": (
        "आत्मविश्वास, अधिकार, नेतृत्व, पिता और सरकारी/प्रशासनिक विषय"
    ),

    "Moon": (
        "मन, भावनाएँ, मानसिक शांति, माता और दैनिक अनुभव"
    ),

    "Mars": (
        "ऊर्जा, साहस, भूमि, तकनीकी कार्य, प्रतिस्पर्धा और क्रियाशीलता"
    ),

    "Mercury": (
        "बुद्धि, संचार, व्यापार, गणना, शिक्षा और निर्णय क्षमता"
    ),

    "Jupiter": (
        "ज्ञान, गुरु, धर्म, विस्तार, संतान, धन और अवसर"
    ),

    "Venus": (
        "प्रेम, विवाह, सुख-सुविधा, कला, वाहन और भौतिक आनंद"
    ),

    "Saturn": (
        "कर्म, अनुशासन, देरी, जिम्मेदारी, श्रम और दीर्घकालिक परिणाम"
    ),

    "Rahu": (
        "महत्वाकांक्षा, असामान्य अवसर, तकनीक, विदेशी संपर्क और भ्रम"
    ),

    "Ketu": (
        "वैराग्य, आध्यात्मिकता, अलगाव, अंतर्दृष्टि और अचानक दिशा परिवर्तन"
    ),
}


# ============================================================
# SPECIAL DRISHTI
# ============================================================
#
# Every graha has the 7th aspect.
#
# Classical special aspects:
# Mars    -> 4th, 7th, 8th
# Jupiter -> 5th, 7th, 9th
# Saturn  -> 3rd, 7th, 10th
#
# Rahu/Ketu aspect conventions vary across traditions.
# We therefore keep them at 7th aspect only in this version.
# ============================================================

SPECIAL_ASPECTS = {

    "Sun": {7},
    "Moon": {7},
    "Mars": {4, 7, 8},
    "Mercury": {7},
    "Jupiter": {5, 7, 9},
    "Venus": {7},
    "Saturn": {3, 7, 10},
    "Rahu": {7},
    "Ketu": {7},
}


# ============================================================
# GRAHA STRENGTH / INTERPRETATION LANGUAGE
# ============================================================

FAVOURABLE_LANGUAGE = {
    "Sun": "सक्रियता, आत्मविश्वास और नेतृत्व के लिए बेहतर संकेत",
    "Moon": "भावनात्मक संतुलन और दैनिक कार्यों में सहयोग",
    "Mars": "साहस, प्रयास और प्रतिस्पर्धा में ऊर्जा",
    "Mercury": "बुद्धि, संचार और व्यापारिक निर्णयों में सहयोग",
    "Jupiter": "विकास, ज्ञान, मार्गदर्शन और अवसरों का समर्थन",
    "Venus": "रिश्तों, सुख-सुविधाओं और रचनात्मकता में सहयोग",
    "Saturn": "मेहनत और अनुशासन से स्थायी परिणाम बनाने का अवसर",
    "Rahu": "नई दिशा, तकनीक और असामान्य अवसरों की संभावना",
    "Ketu": "आंतरिक समझ, शोध और आध्यात्मिक चिंतन का अवसर",
}


CHALLENGING_LANGUAGE = {
    "Sun": "अहंकार, अधिकार या पिता/प्रशासन से जुड़े मामलों में सावधानी",
    "Moon": "मानसिक अस्थिरता या भावनात्मक दबाव की संभावना",
    "Mars": "जल्दबाजी, विवाद और अनावश्यक जोखिम से बचना उचित",
    "Mercury": "गलत संचार, भ्रम या निर्णय में जल्दबाजी से बचना चाहिए",
    "Jupiter": "अतिआत्मविश्वास या अपेक्षाओं के बढ़ने पर संयम जरूरी",
    "Venus": "रिश्तों और खर्चों में संतुलन बनाए रखना जरूरी",
    "Saturn": "देरी, अतिरिक्त जिम्मेदारी और धैर्य की आवश्यकता",
    "Rahu": "भ्रम, अति-महत्वाकांक्षा और जल्दबाजी से सावधानी",
    "Ketu": "अलगाव, अनिश्चितता या निर्णय में अस्थिरता से सावधानी",
}


# ============================================================
# BASIC FUNCTIONS
# ============================================================

def relative_house(transit_sign_index, rashi_index):
    """
    Count the transit sign from the reference Moon sign.

    Example:

    Moon sign = Aries (0)
    Transit = Cancer (3)

    Cancer is the 4th from Aries.
    """

    return (
        (transit_sign_index - rashi_index) % 12
    ) + 1


def aspect_houses(planet):
    """
    Return the houses aspected by the planet.
    """

    return SPECIAL_ASPECTS.get(
        planet,
        {7}
    )


def is_favourable_transit(planet, house):
    """
    Determine whether the graha is in one of its generally
    supportive transit houses from Chandra Rashi.
    """

    return house in FAVOURABLE_HOUSES.get(
        planet,
        set()
    )


def aspect_strength(planet, target_house_from_moon):
    """
    Determine whether a planet's special aspect reaches the
    natal Moon reference sign.

    target_house_from_moon is the house occupied by the planet
    from the Moon sign.

    We calculate the reverse distance from the planet's sign
    back to the Moon sign.
    """

    reverse_house = (
        (12 - target_house_from_moon + 1) % 12
    )

    if reverse_house == 0:
        reverse_house = 12

    if reverse_house in aspect_houses(planet):
        return reverse_house

    return None


# ============================================================
# RETROGRADE MODIFIER
# ============================================================

def retrograde_modifier(planet, retrograde):
    """
    Hindi interpretation modifier for retrograde motion.
    """

    if not retrograde:
        return ""

    if planet == "Saturn":
        return (
            "वक्री गति के कारण पुराने दायित्वों और लंबित मामलों "
            "की पुनर्समीक्षा का संकेत बढ़ सकता है।"
        )

    if planet == "Jupiter":
        return (
            "वक्री गुरु के कारण पुराने ज्ञान, योजनाओं और "
            "निर्णयों की पुनर्समीक्षा महत्वपूर्ण हो सकती है।"
        )

    if planet == "Mars":
        return (
            "वक्री मंगल में ऊर्जा को जल्दबाजी के बजाय "
            "सोच-समझकर उपयोग करना उचित रहेगा।"
        )

    if planet == "Mercury":
        return (
            "वक्री बुध में संचार, दस्तावेज और निर्णयों को "
            "दोबारा जांचना विशेष रूप से उपयोगी रहेगा।"
        )

    if planet == "Venus":
        return (
            "वक्री शुक्र में रिश्तों, खर्चों और पुरानी इच्छाओं "
            "की पुनर्समीक्षा हो सकती है।"
        )

    if planet == "Rahu":
        return (
            "राहु को परंपरागत रूप से वक्री गति वाला माना जाता है; "
            "इसलिए इसे अलग से सामान्य retrograde trigger नहीं माना गया है।"
        )

    if planet == "Ketu":
        return (
            "केतु को परंपरागत रूप से वक्री गति वाला माना जाता है; "
            "इसलिए इसे अलग से सामान्य retrograde trigger नहीं माना गया है।"
        )

    return "वक्री गति के कारण इस ग्रह से जुड़े पुराने विषयों की पुनर्समीक्षा महत्वपूर्ण हो सकती है।"


# ============================================================
# MAIN VEDIC INTERPRETATION
# ============================================================

def interpret_for_rashi(
    planet,
    transit_sign_index,
    rashi_index,
    retrograde=False
):
    """
    Generate a concise Vedic transit interpretation for one
    Rashi, using Chandra Rashi as the reference.

    This function intentionally remains compatible with the
    previous call:

        interpret_for_rashi(planet, transit_sign_index, rashi_index)

    The optional retrograde parameter can be used by the
    upgraded content engine later.
    """

    house = relative_house(
        transit_sign_index,
        rashi_index
    )

    planet_name = PLANET_HI.get(
        planet,
        planet
    )

    sign_name = SIGN_HI[
        transit_sign_index
    ]

    theme = HOUSE_THEMES[
        house
    ]

    favourable = is_favourable_transit(
        planet,
        house
    )

    if favourable:

        result = (
            f"{planet_name} {sign_name} राशि में "
            f"{rashi_index + 1}वीं राशि से {house}वें भाव में "
            f"गोचर कर रहा है। "
            f"यह {theme} से जुड़े मामलों में "
            f"{FAVOURABLE_LANGUAGE.get(planet, 'सहयोग')} "
            f"का संकेत दे सकता है।"
        )

    else:

        result = (
            f"{planet_name} {sign_name} राशि में "
            f"{rashi_index + 1}वीं राशि से {house}वें भाव में "
            f"गोचर कर रहा है। "
            f"यह {theme} से जुड़े मामलों में "
            f"अधिक सावधानी और संतुलन की आवश्यकता दिखा सकता है। "
            f"{CHALLENGING_LANGUAGE.get(planet, '')}"
        )

    # --------------------------------------------------------
    # Special aspect to the natal Moon reference
    # --------------------------------------------------------

    aspect = aspect_strength(
        planet,
        house
    )

    if aspect is not None:

        if planet == "Mars":
            result += (
                " साथ ही मंगल की विशेष दृष्टि का प्रभाव "
                "ऊर्जा और सक्रियता को बढ़ा सकता है।"
            )

        elif planet == "Jupiter":
            result += (
                " साथ ही गुरु की विशेष दृष्टि के कारण "
                "ज्ञान, मार्गदर्शन और विस्तार का प्रभाव "
                "अधिक महत्वपूर्ण हो सकता है।"
            )

        elif planet == "Saturn":
            result += (
                " साथ ही शनि की विशेष दृष्टि के कारण "
                "जिम्मेदारी, अनुशासन और धैर्य की परीक्षा हो सकती है।"
            )

        else:
            result += (
                " इस दौरान ग्रह की सप्तम दृष्टि भी "
                "संबंधित विषयों को सक्रिय कर सकती है।"
            )

    # --------------------------------------------------------
    # Retrograde
    # --------------------------------------------------------

    if retrograde and planet not in {
        "Rahu",
        "Ketu"
    }:

        result += " " + retrograde_modifier(
            planet,
            True
        )

    return result


# ============================================================
# DETAILED RASHI SCORE
# ============================================================

def transit_score(
    planet,
    transit_sign_index,
    rashi_index,
    retrograde=False
):
    """
    Numerical score used later by the content engine to rank
    the most important graha influences for each Rashi.

    Range is approximately -3 to +3.
    """

    house = relative_house(
        transit_sign_index,
        rashi_index
    )

    score = 1 if is_favourable_transit(
        planet,
        house
    ) else -1

    # Strong special-aspect planets get additional weight.
    aspect = aspect_strength(
        planet,
        house
    )

    if aspect is not None:

        if planet == "Jupiter":
            score += 2

        elif planet == "Mars":
            score -= 1

        elif planet == "Saturn":
            score -= 1

        else:
            score += 1

    # Retrograde planets receive an additional interpretive
    # weight, but never completely reverse the base result.
    if retrograde and planet not in {
        "Rahu",
        "Ketu"
    }:
        score -= 1

    return max(
        -3,
        min(
            3,
            score
        )
    )


# ============================================================
# RASHI SUMMARY
# ============================================================

def rashi_summary(
    rashi_index,
    positions
):
    """
    Create a structured summary for one Rashi.

    This will be used by the upgraded Hindi content engine.
    """

    influences = []

    total_score = 0

    for position in positions:

        score = transit_score(
            position.planet,
            position.sign_index,
            rashi_index,
            position.retrograde
        )

        text = interpret_for_rashi(
            position.planet,
            position.sign_index,
            rashi_index,
            position.retrograde
        )

        influences.append({
            "planet": position.planet,
            "score": score,
            "text": text,
        })

        total_score += score

    influences.sort(
        key=lambda item: abs(item["score"]),
        reverse=True
    )

    if total_score >= 4:
        overall = "अनुकूल"
    elif total_score <= -4:
        overall = "सावधानी"
    else:
        overall = "मिश्रित"

    return {
        "rashi": SIGN_HI[rashi_index],
        "score": total_score,
        "overall": overall,
        "influences": influences,
    }
