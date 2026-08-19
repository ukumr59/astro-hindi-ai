"""
Vedic Jyotisha Gochar Rules Engine

System:
    Nirayana / Sidereal zodiac
    Lahiri ayanamsha
    Chandra Rashi based Gochar

Purpose:
    Calculate classical transit houses and generate
    structured Hindi interpretations for daily horoscope.
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
# CLASSICAL GOCHARA
# ============================================================

FAVOURABLE_HOUSES = {
    "Sun": {3, 6, 10, 11},
    "Moon": {1, 3, 6, 7, 10, 11},
    "Mars": {3, 6, 10, 11},
    "Mercury": {2, 4, 6, 8, 10, 11},
    "Jupiter": {2, 5, 7, 9, 11},
    "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12},
    "Saturn": {3, 6, 11},
    "Rahu": {3, 6, 10, 11},
    "Ketu": {3, 6, 10, 11},
}

CHALLENGING_HOUSES = {
    "Sun": {1, 2, 4, 5, 7, 8, 9, 12},
    "Moon": {2, 4, 5, 8, 9, 12},
    "Mars": {1, 2, 4, 5, 7, 8, 9, 12},
    "Mercury": {1, 3, 5, 7, 9, 12},
    "Jupiter": {1, 3, 4, 6, 8, 10, 12},
    "Venus": {6, 7, 10},
    "Saturn": {1, 2, 4, 5, 7, 8, 9, 10, 12},
    "Rahu": {1, 2, 4, 5, 7, 8, 9, 12},
    "Ketu": {1, 2, 4, 5, 7, 8, 9, 12},
}


# ============================================================
# SPECIAL DRISHTI
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
# HOUSE THEMES
# ============================================================

HOUSE_THEMES = {
    1: "स्वास्थ्य, व्यक्तित्व और आत्मविश्वास",
    2: "धन, बचत, परिवार और वाणी",
    3: "साहस, प्रयास, संचार और छोटे सफर",
    4: "घर, संपत्ति, माता और मानसिक सुख",
    5: "शिक्षा, बुद्धि, प्रेम और संतान",
    6: "नौकरी, प्रतियोगिता, ऋण और स्वास्थ्य",
    7: "विवाह, साझेदारी और सार्वजनिक संबंध",
    8: "अचानक परिवर्तन, साझा धन और गहन विषय",
    9: "भाग्य, धर्म, गुरु और उच्च शिक्षा",
    10: "करियर, कर्म, प्रतिष्ठा और जिम्मेदारी",
    11: "आय, लाभ, नेटवर्क और इच्छापूर्ति",
    12: "व्यय, विदेश, एकांत और आध्यात्मिक चिंतन",
}


# ============================================================
# PLANET THEMES
# ============================================================

PLANET_THEMES = {
    "Sun": "आत्मविश्वास, नेतृत्व और अधिकार",
    "Moon": "मन, भावनाएं और मानसिक शांति",
    "Mars": "ऊर्जा, साहस और प्रतिस्पर्धा",
    "Mercury": "बुद्धि, संचार, व्यापार और निर्णय",
    "Jupiter": "ज्ञान, विस्तार, गुरु और अवसर",
    "Venus": "प्रेम, विवाह, सुख-सुविधा और कला",
    "Saturn": "कर्म, अनुशासन, जिम्मेदारी और मेहनत",
    "Rahu": "महत्वाकांक्षा, तकनीक और विदेशी संपर्क",
    "Ketu": "वैराग्य, शोध और आध्यात्मिकता",
}


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
# HOUSE FROM MOON SIGN
# ============================================================

def relative_house(
    transit_sign_index,
    rashi_index
):
    return (
        (transit_sign_index - rashi_index) % 12
    ) + 1


# ============================================================
# DRISHTI
# ============================================================

def get_aspected_houses(
    planet,
    transit_house
):
    result = []

    for aspect in SPECIAL_ASPECTS.get(
        planet,
        {7}
    ):
        target = (
            (transit_house - 1 + aspect - 1) % 12
        ) + 1

        result.append(
            target
        )

    return sorted(
        set(result)
    )


def aspect_names(planet):

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

def transit_quality(
    planet,
    house
):
    """
    Classical general Gochar quality.

    +2 strongly favourable
    +1 favourable
     0 neutral
    -1 challenging
    """

    if house in FAVOURABLE_HOUSES.get(
        planet,
        set()
    ):

        if planet in {
            "Saturn",
            "Jupiter",
            "Mars",
            "Sun",
        }:
            return 2

        return 1

    if house in CHALLENGING_HOUSES.get(
        planet,
        set()
    ):
        return -1

    return 0


# ============================================================
# INDIVIDUAL PLANET SCORE
# ============================================================

def transit_score(
    planet,
    transit_sign_index,
    rashi_index,
    retrograde=False
):

    house = relative_house(
        transit_sign_index,
        rashi_index
    )

    score = transit_quality(
        planet,
        house
    )

    if (
        retrograde
        and planet not in {
            "Rahu",
            "Ketu",
        }
    ):

        if score > 0:
            score -= 1

    return max(
        -2,
        min(
            2,
            score
        )
    )


# ============================================================
# RETROGRADE
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
            "कार्यों की पुनर्समीक्षा का संकेत देता है।"
        )

    if planet == "Jupiter":
        return (
            "वक्री गुरु पुराने निर्णयों और योजनाओं "
            "की पुनर्समीक्षा का संकेत देता है।"
        )

    if planet == "Mercury":
        return (
            "वक्री बुध में संचार और दस्तावेजों "
            "को दोबारा जांचना उपयोगी रहेगा।"
        )

    if planet == "Venus":
        return (
            "वक्री शुक्र में रिश्तों और खर्चों की "
            "समीक्षा हो सकती है।"
        )

    if planet == "Mars":
        return (
            "वक्री मंगल में ऊर्जा का उपयोग "
            "योजनाबद्ध तरीके से करना बेहतर रहेगा।"
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

    house = relative_house(
        transit_sign_index,
        rashi_index
    )

    sign_name = SIGN_HI[
        transit_sign_index
    ]

    name = PLANET_HI.get(
        planet,
        planet
    )

    house_theme = HOUSE_THEMES.get(
        house,
        "जीवन के महत्वपूर्ण विषय"
    )

    theme = PLANET_THEMES.get(
        planet,
        "ग्रह संबंधी विषय"
    )

    quality = transit_quality(
        planet,
        house
    )

    if quality > 0:

        text = (
            f"{name} {sign_name} राशि में "
            f"{house_text(house)} भाव में गोचर कर रहा है। "
            f"इससे {house_theme} से जुड़े मामलों में "
            f"{theme} को सकारात्मक दिशा मिल सकती है।"
        )

    elif quality < 0:

        text = (
            f"{name} {sign_name} राशि में "
            f"{house_text(house)} भाव में गोचर कर रहा है। "
            f"{house_theme} से जुड़े मामलों में "
            f"धैर्य और संतुलन बनाए रखना जरूरी रहेगा।"
        )

    else:

        text = (
            f"{name} {sign_name} राशि में "
            f"{house_text(house)} भाव में गोचर कर रहा है। "
            f"{house_theme} से जुड़े मामलों में "
            f"सामान्य प्रभाव दिखाई दे सकता है।"
        )

    if planet in {
        "Mars",
        "Jupiter",
        "Saturn",
    }:

        targets = get_aspected_houses(
            planet,
            house
        )

        target_text = ", ".join(
            house_text(
                target
            )
            for target in targets
        )

        text += (
            f" {aspect_names(planet)} "
            f"{target_text} भावों को भी प्रभावित करती है।"
        )

    retro = retrograde_modifier(
        planet,
        retrograde
    )

    if retro:
        text += " " + retro

    return text


# ============================================================
# OVERALL CLASSIFICATION
# ============================================================

def classify_rashi(
    influences
):
    """
    Determine overall Rashi quality from the strongest
    classical transit influences.

    Important principle:
    A strong Jupiter/Saturn/Rahu/Ketu transit should not
    be cancelled by several weak fast-planet transits.

    Priority:
        Jupiter / Saturn / Rahu / Ketu
        Mars
        Sun / Mercury / Venus
        Moon
    """

    slow = []
    medium = []
    fast = []

    for item in influences:

        planet = item["planet"]
        score = item["score"]

        if planet in {
            "Jupiter",
            "Saturn",
            "Rahu",
            "Ketu",
        }:
            slow.append(score)

        elif planet == "Mars":
            medium.append(score)

        else:
            fast.append(score)

    slow_positive = sum(
        1
        for score in slow
        if score > 0
    )

    slow_negative = sum(
        1
        for score in slow
        if score < 0
    )

    medium_positive = sum(
        1
        for score in medium
        if score > 0
    )

    medium_negative = sum(
        1
        for score in medium
        if score < 0
    )

    # Strong favourable slow-planet transit.
    if slow_positive > slow_negative:
        return "अनुकूल"

    # Strong challenging slow-planet dominance.
    if slow_negative > slow_positive:
        return "सावधानी"

    # Mars can decide the day when slow planets are neutral.
    if medium_positive > medium_negative:
        return "अनुकूल"

    if medium_negative > medium_positive:
        return "सावधानी"

    # Fast planets decide only when the major planets
    # are balanced.
    fast_score = sum(
        fast
    )

    if fast_score >= 2:
        return "अनुकूल"

    if fast_score <= -2:
        return "सावधानी"

    return "मिश्रित"


# ============================================================
# NUMERICAL SCORE FOR RANKING ONLY
# ============================================================

def ranking_score(
    influences
):

    weights = {
        "Jupiter": 5.0,
        "Saturn": 5.0,
        "Rahu": 4.0,
        "Ketu": 4.0,
        "Mars": 3.0,
        "Sun": 1.5,
        "Mercury": 1.0,
        "Venus": 1.0,
        "Moon": 0.5,
    }

    total = 0.0

    for item in influences:

        planet = item["planet"]

        score = item["score"]

        total += (
            score
            * weights.get(
                planet,
                1.0
            )
        )

    return round(
        total,
        2
    )


# ============================================================
# RASHI SUMMARY
# ============================================================

def rashi_summary(
    rashi_index,
    positions
):

    influences = []

    for position in positions:

        house = relative_house(
            position.sign_index,
            rashi_index
        )

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
            "house": house,
            "text": text,
            "retrograde": position.retrograde,
        })

    # Strongest first.
    influences.sort(
        key=lambda item: (
            abs(
                item["score"]
            ),
            item["score"]
        ),
        reverse=True
    )

    score = ranking_score(
        influences
    )

    overall = classify_rashi(
        influences
    )

    return {
        "rashi": SIGN_HI[
            rashi_index
        ],
        "score": score,
        "overall": overall,
        "influences": influences,
    }
