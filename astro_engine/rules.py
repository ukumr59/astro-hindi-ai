PLANET_HI = {
    "Sun": "सूर्य", "Moon": "चंद्रमा", "Mars": "मंगल",
    "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र",
    "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"
}

SIGN_HI = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"
]

HOUSE_THEMES = {
    1: "व्यक्तित्व, आत्मविश्वास और नई शुरुआत",
    2: "धन, परिवार और वाणी",
    3: "प्रयास, संचार और छोटे सफर",
    4: "घर, संपत्ति और पारिवारिक सुख",
    5: "शिक्षा, रचनात्मकता और प्रेम",
    6: "प्रतिस्पर्धा, काम और दिनचर्या",
    7: "साझेदारी और रिश्ते",
    8: "अचानक बदलाव, साझा धन और गहराई",
    9: "भाग्य, उच्च शिक्षा और यात्रा",
    10: "करियर, प्रतिष्ठा और जिम्मेदारी",
    11: "आय, लाभ और नेटवर्क",
    12: "खर्च, विश्राम और दूरस्थ अवसर"
}

def relative_house(transit_sign_index, rashi_index):
    return ((transit_sign_index - rashi_index) % 12) + 1

def interpret_for_rashi(planet, transit_sign_index, rashi_index):
    house = relative_house(transit_sign_index, rashi_index)
    theme = HOUSE_THEMES[house]
    p = PLANET_HI.get(planet, planet)
    return f"{p} का प्रभाव {house}वें भाव के {theme} से जुड़े विषयों को सक्रिय कर सकता है।"
