"""
Vedic / Jyotisha transit rules.

Method:
    - Nirayana / sidereal zodiac
    - Lahiri ayanamsha positions
    - Chandra Rashi as the mass-horoscope reference
    - Transit houses counted from Chandra Rashi
    - Classical graha gochara tendencies
    - Classical graha drishti
    - Rahu/Ketu treated as shadow planets
    - Retrograde motion used as an interpretive modifier

This is a rule-based Jyotisha interpretation system.
It is not a scientific prediction system.
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
    1: "स्वास्थ्य, व्यक्तित्व, आत्मविश्वास और व्यक्तिगत निर्णय",
    2: "धन, बचत, परिवार और वाणी",
    3: "साहस, प्रयास, संचार और छोटे सफर",
    4: "घर, संपत्ति, माता और मानसिक सुख",
    5: "शिक्षा, बुद्धि, रचनात्मकता, प्रेम और संतान",
    6: "नौकरी, प्रतियोगिता, ऋण, रोग और दैनिक दिनचर्या",
    7: "विवाह, साझेदारी, संबंध और सार्वजनिक व्यवहार",
    8: "अचानक परिवर्तन, साझा धन, शोध और गहन विषय",
    9: "भाग्य, धर्म, गुरु, उच्च शिक्षा और लंबी यात्रा",
    10: "करियर, कर्म, प्रतिष्ठा और जिम्मेदारी",
    11: "आय, लाभ, इच्छापूर्ति और नेटवर्क",
    12: "व्यय, विदेश, एकांत, विश्राम और आध्यात्मिक चिंतन",
}


# ============================================================
# CLASSICAL GOCHARA
# ============================================================

FAVOURABLE_HOUSES = {
    "Sun": {3, 6, 10, 11},
    "Moon": {1, 3, 6, 7, 10, 11},
    "Mars": {3, 6, 11},
    "Mercury": {2, 4, 6, 8, 10, 11},
    "Jupiter": {2, 5, 7, 9, 11},
    "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12},
    "Saturn": {3, 6, 11},
    "Rahu": {3, 6, 10, 11},
    "Ketu": {3, 6, 10, 11},
}


# ============================================================
# CLASSICAL SPECIAL DRISHTI
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
# PLANET THEMES
# ============================================================

PLANET_THEMES = {
    "Sun": "आत्मविश्वास, नेतृत्व, अधिकार, पिता और प्रशासन",
    "Moon": "मन, भावनाएं, मानसिक शांति और दैनिक अनुभव",
    "Mars": "ऊर्जा, साहस, भूमि, तकनीकी कार्य और प्रतिस्पर्धा",
    "Mercury": "बुद्धि, संचार, व्यापार, गणना और निर्णय",
    "Jupiter": "ज्ञान, गुरु, धर्म, विस्तार, संतान और अवसर",
    "Venus": "प्रेम, विवाह, सुख-सुविधा, कला और वाहन",
    "Saturn": "कर्म, अनुशासन, जिम्मेदारी, श्रम और देरी",
    "Rahu": "महत्वाकांक्षा, तकनीक, विदेशी संपर्क और असामान्य अवसर",
    "Ketu": "वैराग्य, आध्यात्मिकता, शोध और अलगाव",
}


# ============================================================
# GENERAL POSITIVE / CHALLENGING LANGUAGE
# ============================================================

POSITIVE_LANGUAGE = {
    "Sun": "आत्मविश्वास और नेतृत्व को बढ़ावा मिल सकता है",
    "Moon": "भावनात्मक संतुलन और सहयोग मिल सकता है",
    "Mars": "साहस और प्रयासों को गति मिल सकती है",
    "Mercury": "बुद्धि, संचार और व्यापारिक निर्णयों में सहायता मिल सकती है",
    "Jupiter": "विकास, ज्ञान और अवसरों का समर्थन मिल सकता है",
    "Venus": "रिश्तों, सुख-सुविधाओं और रचनात्मक कार्यों में सहयोग मिल सकता है",
    "Saturn": "अनुशासन और निरंतर मेहनत से स्थायी परिणाम मिल सकते हैं",
    "Rahu": "नई दिशा और असामान्य अवसर सामने आ सकते हैं",
    "Ketu": "आंतरिक समझ और शोध की प्रवृत्ति बढ़ सकती है",
}


CHALLENGING_LANGUAGE = {
    "Sun": "अहंकार और अधिकार से जुड़े विवादों से बचना उचित रहेगा",
    "Moon": "भावनात्मक प्रतिक्रिया देने के बजाय धैर्य रखना उपयोगी रहेगा",
    "Mars": "जल्दबाजी, विवाद और अनावश्यक जोखिम से बचना चाहिए",
    "Mercury": "संचार और दस्तावेजों को दोबारा जांचना उचित रहेगा",
    "Jupiter": "अति-आशावाद और अनावश्यक विस्तार से बचना चाहिए",
    "Venus": "रिश्तों और खर्चों में संतुलन बनाए रखना जरूरी रहेगा",
    "Saturn": "देरी और अतिरिक्त जिम्मेदारियों के कारण धैर्य की आवश्यकता रहेगी",
    "Rahu": "भ्रम और जल्दबाजी में निर्णय लेने से बचना चाहिए",
    "Ketu": "अलगाव या अनिश्चितता के कारण निर्णय सोच-समझकर लेना चाहिए",
}


# ============================================================
# HOUSE ORDINALS
# ============================================================

HOUSE_ORDINAL_HI = {
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


def house_text(house):
    return HOUSE_ORDINAL_HI.get(
        house,
        str(house)
    )


# ============================================================
# BASIC HOUSE CALCULATION
# ============================================================

def relative_house(transit_sign_index, rashi_index):
    """
    Count a transit sign from the Chandra Rashi.

    Example:
        Moon sign = Aries
        Transit sign = Cancer

        Cancer is the 4th house from Aries.
    """

    return (
        (transit_sign_index - rashi_index) % 12
    ) + 1


# ============================================================
# ASPECT CALCULATION
# ============================================================

def aspect_houses(planet):
    return SPECIAL_ASPECTS.get(
        planet,
        {7}
    )


def get_aspected_houses(planet, transit_house):
    """
    Return the houses from Chandra Rashi receiving
    the planet's classical drishti.
    """

    result = []

    for aspect in aspect_houses(planet):

        target = (
            (transit_house - 1 + aspect - 1) % 12
        ) + 1

        result.append(target)

    return sorted(set(result))


def aspect_names(planet):
    """
    Human-readable description of special drishti.
    """

    if planet == "Mars":
        return "मंगल की 4वीं, 7वीं और 8वीं दृष्टि"

    if planet == "Jupiter":
        return "गुरु की 5वीं, 7वीं और 9वीं दृष्टि"

    if planet == "Saturn":
        return "शनि की 3वीं, 7वीं और 10वीं दृष्टि"

    return "ग्रह की 7वीं दृष्टि"


# ============================================================
# TRANSIT QUALITY
# ============================================================

def is_favourable_transit(planet, house):
    return house in FAVOURABLE_HOUSES.get(
        planet,
        set()
    )


def transit_score(
    planet,
    transit_sign_index,
    rashi_index,
    retrograde=False
):
    """
    Approximate interpretive score.

    This is NOT a scientific score.
    It is only used to rank which transit influences
    should receive more narration time.
    """

    house = relative_house(
        transit_sign_index,
        rashi_index
    )

    score = 1 if is_favourable_transit(
        planet,
        house
    ) else -1

    # Classical special drishti.
    aspected = get_aspected_houses(
        planet,
        house
    )

    # Give additional weight to the classical
    # special-aspect planets.
    if planet == "Jupiter" and aspected:
        score += 1

    if planet in {"Mars", "Saturn"} and aspected:
        score -= 1

    # Retrograde is an interpretive modifier.
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
# RETROGRADE LANGUAGE
# ============================================================

def retrograde_modifier(
    planet,
    retrograde
):
    if not retrograde:
        return ""

    if planet == "Saturn":
        return (
            "वक्री शनि पुराने दायित्वों और लंबित "
            "मामलों की पुनर्समीक्षा का संकेत देता है।"
        )

    if planet == "Jupiter":
        return (
            "वक्री गुरु पुराने निर्णयों, योजनाओं और "
            "ज्ञान की पुनर्समीक्षा की ओर संकेत करता है।"
        )

    if planet == "Mercury":
        return (
            "वक्री बुध में संचार, दस्तावेज और "
            "निर्णयों को दोबारा जांचना उपयोगी रहता है।"
        )

    if planet == "Venus":
        return (
            "वक्री शुक्र में रिश्तों, खर्चों और "
            "पुरानी इच्छाओं की समीक्षा हो सकती है।"
        )

    if planet == "Mars":
        return (
            "वक्री मंगल में जल्दबाजी के बजाय "
            "ऊर्जा का योजनाबद्ध उपयोग बेहतर रहता है।"
        )

    return ""


# ============================================================
# PLANET INTERPRETATION
# ============================================================

def interpret_for_rashi(
    planet,
    transit_sign_index,
    rashi_index,
    retrograde=False
):
    """
    Generate a clean Hindi interpretation.

    Chandra Rashi is the reference point.
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

    if is_favourable_transit(
        planet,
        house
    ):
        sentence = (
            f"{planet_name} {sign_name} में "
            f"{house_text(house)} भाव में गोचर कर रहा है। "
            f"यह {theme} से जुड़े मामलों में "
            f"{POSITIVE_LANGUAGE.get(planet, 'सहयोग')}।"
        )
    else:
        sentence = (
            f"{planet_name} {sign_name} में "
            f"{house_text(house)} भाव में गोचर कर रहा है। "
            f"यह {theme} से जुड़े मामलों में "
            f"धैर्य और संतुलन की आवश्यकता दिखाता है। "
            f"{CHALLENGING_LANGUAGE.get(planet, '')}।"
        )

    # Special drishti.
    if planet in {
        "Mars",
        "Jupiter",
        "Saturn"
    }:

        targets = get_aspected_houses(
            planet,
            house
        )

        target_text = ", ".join(
            house_text(h)
            for h in targets
        )

        sentence += (
            f" {aspect_names(planet)} "
            f"{target_text} भावों को भी सक्रिय करती है।"
        )

    # Retrograde.
    retro = retrograde_modifier(
        planet,
        retrograde
    )

    if retro:
        sentence += " " + retro

    return sentence


# ============================================================
# RASHI SUMMARY
# ============================================================

def rashi_summary(
    rashi_index,
    positions
):
    """
    Create structured daily transit analysis for one Rashi.
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

        house = relative_house(
            position.sign_index,
            rashi_index
        )

        influences.append({
            "planet": position.planet,
            "score": score,
            "house": house,
            "text": text,
        })

        total_score += score

    influences.sort(
        key=lambda item: (
            abs(item["score"]),
            item["score"]
        ),
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
