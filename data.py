# data.py
# Единый источник данных (тарифы / расписание / география / контакты)

ROUTES = {
    "neft_tyumen": {"label": "Нефтеюганск → Тюмень"},
    "surgut_tyumen": {"label": "Сургут → Тюмень"},
    "kogalym_tyumen": {"label": "Когалым → Тюмень"},
    "noyabrsk_tyumen": {"label": "Ноябрьск → Тюмень"},
}

WEIGHT_BANDS = {
    "w_0_3": {"label": "0,1–3 кг", "range": (0.1, 3)},
    "w_4_30": {"label": "4–30 кг", "range": (4, 30)},
    "w_31_60": {"label": "31–60 кг", "range": (31, 60)},
    "w_60_plus": {"label": "60+ кг (индивидуально)", "range": (60.0001, 10_000)},
}

# ТАРИФЫ: (маршрут, вес_категория) -> цена
TARIFFS = {
    ("neft_tyumen", "w_0_3"): 250,
    ("neft_tyumen", "w_4_30"): 350,
    ("neft_tyumen", "w_31_60"): 700,

    ("surgut_tyumen", "w_0_3"): 300,
    ("surgut_tyumen", "w_4_30"): 400,
    ("surgut_tyumen", "w_31_60"): 800,

    ("kogalym_tyumen", "w_0_3"): 500,
    ("kogalym_tyumen", "w_4_30"): 1000,
    ("kogalym_tyumen", "w_31_60"): 2000,

    ("noyabrsk_tyumen", "w_0_3"): 500,
    ("noyabrsk_tyumen", "w_4_30"): 1000,
    ("noyabrsk_tyumen", "w_31_60"): 2000,
}

SCHEDULE = [
    {"route": "Сургут ↔ Тюмень", "days": "ежедневно (7/7)"},
    {"route": "Ноябрьск ↔ Тюмень", "days": "Понедельник, Пятница"},
    {"route": "Тюмень ↔ Когалым ↔ Ноябрьск", "days": "Четверг, Воскресенье"},
]

GEO = ["Тюмень", "Тобольск", "Нефтеюганск", "Сургут", "Ноябрьск", "Муравленко"]

CONTACTS = {
    "tg": "t.me/SVOIEXPRESSS",
    "phone": "+7 922 939 9799",
}
