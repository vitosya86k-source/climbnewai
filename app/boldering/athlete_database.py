"""База данных 16 спортсменов для сравнения"""

ATHLETE_DATABASE = {
    # ========== ПРОФЕССИОНАЛЫ (4) ==========
    "adam_ondra": {
        "name": "Adam Ondra",
        "level": "pro",
        "avg_quality": 95,
        "avg_intensity": 22,
        "style": "technical",
        "description": "Технический перфекционист с невероятным контролем",
        "strengths": ["Техника", "Выносливость", "Ментальная устойчивость"],
        "specialty": "Технические плиты и нависания"
    },
    "alex_megos": {
        "name": "Alex Megos",
        "level": "pro",
        "avg_quality": 93,
        "avg_intensity": 28,
        "style": "dynamic",
        "description": "Динамичный и мощный, любит сложные координационные задачи",
        "strengths": ["Динамика", "Сила", "Скорость"],
        "specialty": "Динамичные трассы с большими движениями"
    },
    "janja_garnbret": {
        "name": "Janja Garnbret",
        "level": "pro",
        "avg_quality": 96,
        "avg_intensity": 20,
        "style": "versatile",
        "description": "Универсал с невероятной адаптивностью",
        "strengths": ["Универсальность", "Адаптация", "Эффективность"],
        "specialty": "Любые типы трасс"
    },
    "tomoa_narasaki": {
        "name": "Tomoa Narasaki",
        "level": "pro",
        "avg_quality": 94,
        "avg_intensity": 30,
        "style": "speed",
        "description": "Быстрый и взрывной, отличная координация",
        "strengths": ["Скорость", "Координация", "Взрывная сила"],
        "specialty": "Скоростные болдеры"
    },
    
    # ========== ПРОДВИНУТЫЕ (4) ==========
    "advanced_1": {
        "name": "Продвинутый скалолаз A",
        "level": "advanced",
        "avg_quality": 85,
        "avg_intensity": 19,
        "style": "technical",
        "description": "Сильный технический подход с фокусом на эффективность",
        "strengths": ["Техника", "Планирование", "Экономия сил"],
        "specialty": "Технические трассы"
    },
    "advanced_2": {
        "name": "Продвинутый скалолаз B",
        "level": "advanced",
        "avg_quality": 83,
        "avg_intensity": 26,
        "style": "power",
        "description": "Силовой подход с акцентом на мощные движения",
        "strengths": ["Сила", "Мощность", "Нависания"],
        "specialty": "Силовые трассы"
    },
    "advanced_3": {
        "name": "Продвинутый скалолаз C",
        "level": "advanced",
        "avg_quality": 84,
        "avg_intensity": 18,
        "style": "endurance",
        "description": "Выносливость и методичность",
        "strengths": ["Выносливость", "Стабильность", "Терпение"],
        "specialty": "Длинные трассы"
    },
    "advanced_4": {
        "name": "Продвинутый скалолаз D",
        "level": "advanced",
        "avg_quality": 82,
        "avg_intensity": 23,
        "style": "versatile",
        "description": "Универсальный стиль с балансом всех навыков",
        "strengths": ["Баланс", "Адаптация", "Универсальность"],
        "specialty": "Разнообразные трассы"
    },
    
    # ========== СРЕДНИЙ УРОВЕНЬ (4) ==========
    "intermediate_1": {
        "name": "Средний скалолаз A",
        "level": "intermediate",
        "avg_quality": 72,
        "avg_intensity": 22,
        "style": "learning",
        "description": "Активно учится и развивает базовые навыки",
        "strengths": ["Мотивация", "Прогресс", "Открытость"],
        "specialty": "Базовые технические трассы"
    },
    "intermediate_2": {
        "name": "Средний скалолаз B",
        "level": "intermediate",
        "avg_quality": 75,
        "avg_intensity": 20,
        "style": "developing",
        "description": "Развивает технику и контроль",
        "strengths": ["Контроль", "Техника", "Внимательность"],
        "specialty": "Плиты средней сложности"
    },
    "intermediate_3": {
        "name": "Средний скалолаз C",
        "level": "intermediate",
        "avg_quality": 70,
        "avg_intensity": 25,
        "style": "building",
        "description": "Строит силу и выносливость",
        "strengths": ["Усердие", "Упорство", "Физическое развитие"],
        "specialty": "Силовые болдеры средней сложности"
    },
    "intermediate_4": {
        "name": "Средний скалолаз D",
        "level": "intermediate",
        "avg_quality": 73,
        "avg_intensity": 24,
        "style": "progressing",
        "description": "Стабильно прогрессирует во всех аспектах",
        "strengths": ["Стабильность", "Прогресс", "Систематичность"],
        "specialty": "Универсальные трассы средней сложности"
    },
    
    # ========== НОВИЧКИ (4) ==========
    "beginner_1": {
        "name": "Начинающий скалолаз A",
        "level": "beginner",
        "avg_quality": 55,
        "avg_intensity": 28,
        "style": "foundation",
        "description": "Закладывает основы, высокая интенсивность из-за напряжения",
        "strengths": ["Энтузиазм", "Энергия", "Желание учиться"],
        "specialty": "Простые вертикальные стены"
    },
    "beginner_2": {
        "name": "Начинающий скалолаз B",
        "level": "beginner",
        "avg_quality": 58,
        "avg_intensity": 24,
        "style": "basics",
        "description": "Осваивает базовые техники",
        "strengths": ["Внимательность", "Обучаемость", "Терпение"],
        "specialty": "Простые технические элементы"
    },
    "beginner_3": {
        "name": "Начинающий скалолаз C",
        "level": "beginner",
        "avg_quality": 52,
        "avg_intensity": 30,
        "style": "learning",
        "description": "В процессе активного обучения",
        "strengths": ["Активность", "Пробы", "Эксперименты"],
        "specialty": "Разнообразные простые трассы"
    },
    "beginner_4": {
        "name": "Начинающий скалолаз D",
        "level": "beginner",
        "avg_quality": 60,
        "avg_intensity": 22,
        "style": "developing",
        "description": "Развивает понимание движений",
        "strengths": ["Аналитика", "Наблюдательность", "Рост"],
        "specialty": "Технические простые трассы"
    }
}


def get_level_numeric(level: str) -> int:
    """Конвертация уровня в число для сравнения"""
    return {
        "beginner": 1,
        "intermediate": 2,
        "advanced": 3,
        "pro": 4
    }[level]


def get_level_name_ru(level: str) -> str:
    """Перевод уровня на русский"""
    return {
        "beginner": "Начинающий",
        "intermediate": "Средний",
        "advanced": "Продвинутый",
        "pro": "Профессионал"
    }[level]


