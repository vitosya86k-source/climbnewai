"""Клавиатуры для Telegram бота с BoulderVision"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная закрепленная клавиатура (MVP - только помощь)"""
    keyboard = [
        ["❓ Помощь"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_overlay_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора типа визуализации v6.0
    
    ТОЛЬКО полный анализ - сразу начинаем обработку
    """
    keyboard = [
        [
            InlineKeyboardButton("🎯 Полный анализ", callback_data="overlay_done"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_overlay_extended_keyboard() -> InlineKeyboardMarkup:
    """
    Расширенная клавиатура с дополнительными визуализациями
    """
    keyboard = [
        [
            InlineKeyboardButton("🧠 Карта решений", callback_data="overlay_decision_map"),
            InlineKeyboardButton("👻 Призрак", callback_data="overlay_ghost_comparison"),
        ],
        [
            InlineKeyboardButton("🎯 Зацепы", callback_data="overlay_holds"),
            InlineKeyboardButton("📊 Метрики", callback_data="overlay_metrics"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data="overlay_show_main"),
            InlineKeyboardButton("✅ Готово", callback_data="overlay_done"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_basic_overlay_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с основными визуализациями (без продвинутых)"""
    keyboard = [
        [
            InlineKeyboardButton("📍 Центр масс", callback_data="overlay_center"),
            InlineKeyboardButton("🔥 Напряжение", callback_data="overlay_stress"),
        ],
        [
            InlineKeyboardButton("📊 Метрики", callback_data="overlay_metrics"),
        ],
        [
            InlineKeyboardButton("✅ Готово", callback_data="overlay_done")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_bouldervision_overlay_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура только с BoulderVision визуализациями"""
    keyboard = [
        [
            InlineKeyboardButton("🌡️ Тепловая карта", callback_data="overlay_heatmap"),
        ],
        [
            InlineKeyboardButton("📈 Траектория", callback_data="overlay_trajectory"),
        ],
        [
            InlineKeyboardButton("🎯 Зацепы", callback_data="overlay_holds"),
        ],
        [
            InlineKeyboardButton("⬅️ Базовые", callback_data="show_basic_overlays"),
            InlineKeyboardButton("✅ Готово", callback_data="overlay_done")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_report_format_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора формата отчета"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Технический", callback_data="report_technical"),
            InlineKeyboardButton("😊 Клиентский", callback_data="report_client"),
        ],
        [
            InlineKeyboardButton("🕵️ Детектив", callback_data="report_detective"),
            InlineKeyboardButton("🎮 Геймерский", callback_data="report_gamer"),
        ],
        [
            InlineKeyboardButton("👨‍🎓 Для тренера", callback_data="report_coach"),
            InlineKeyboardButton("💃 Girl Style", callback_data="report_girl_style"),
        ],
        [
            InlineKeyboardButton("💪 Для новичка", callback_data="report_beginner"),
            InlineKeyboardButton("🎲 Рандомный", callback_data="report_random"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_next_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для действий после получения отчета"""
    keyboard = [
        [
            InlineKeyboardButton("🎨 Другая разметка", callback_data="action_another_overlay"),
            InlineKeyboardButton("🔄 Другой отчет", callback_data="action_another_report"),
        ],
        [
            InlineKeyboardButton("📹 Новое видео", callback_data="action_new_video"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_overlay_info() -> dict:
    """
    Возвращает информацию о типах визуализации v3.0

    Принцип "Переломного момента" - Сила Контекста:
    5 ключевых визуализаций + полный анализ

    Returns:
        dict с описаниями каждого типа
    """
    return {
        # Полный анализ - для соцсетей
        'full': {
            'name': '🎯 Полный анализ',
            'description': 'Все метрики на одном видео',
            'when_to_use': 'Хочешь классное видео для соцсетей',
            'solves': 'Увидеть всё сразу',
            'priority': 0
        },
        # 5 ключевых визуализаций
        'spider_metrics': {
            'name': '🕸️ Метрики',
            'description': 'Паутинка: Сила / Баланс / Координация / Техника',
            'when_to_use': 'Хочешь понять свой уровень',
            'solves': 'Объективная оценка техники',
            'priority': 1
        },
        'weight_load': {
            'name': '⚖️ Нагрузка (кг)',
            'description': 'Сколько КГ приходится на каждую руку и ногу',
            'when_to_use': 'Руки забиваются слишком быстро',
            'solves': 'Понять где перегружаешься',
            'priority': 2
        },
        'tension_zones': {
            'name': '⚠️ Зажимы',
            'description': 'Зоны мышечных зажимов и риска травм',
            'when_to_use': 'Болят суставы/мышцы после лазания',
            'solves': 'Предотвратить травмы',
            'priority': 3
        },
        'speed_map': {
            'name': '⏱️ Скорость',
            'description': 'Карта решений и скорость движений',
            'when_to_use': 'Долго думаешь на трассе',
            'solves': 'Ускорить прохождение',
            'priority': 4
        },
        'ideal_ghost': {
            'name': '👻 Призрак-эталон',
            'description': 'Сравнение с идеальным прохождением (призрак опережает)',
            'when_to_use': 'Хочешь улучшить технику',
            'solves': 'Увидеть как должно быть',
            'priority': 5
        }
    }


def get_smart_overlay_recommendation(analysis_data: dict) -> str:
    """
    Умная рекомендация визуализации v3.0

    Принцип "Переломного момента" - Сила Контекста:
    Рекомендуем визуализацию исходя из проблем пользователя
    """
    recommendations = []

    # Анализируем данные и даём контекстные рекомендации
    motion_intensity = analysis_data.get('motion_intensity', 50)
    pose_quality = analysis_data.get('pose_quality', 50)
    energy_drain = analysis_data.get('energy_drain', 0.5)
    stability = analysis_data.get('stability', 50)

    if motion_intensity > 70:
        recommendations.append("⚖️ **Нагрузка (кг)** - высокая активность, проверь распределение веса")

    if energy_drain > 0.7 or stability < 40:
        recommendations.append("⚠️ **Зажимы** - быстро устаёшь, проверь зоны напряжения")

    if pose_quality < 50:
        recommendations.append("🕸️ **Метрики** - техника требует внимания, посмотри на паутинку")

    if motion_intensity < 30:
        recommendations.append("⏱️ **Скорость** - много думаешь на трассе, проверь карту решений")

    if not recommendations:
        recommendations.append("🎯 **Полный анализ** - техника хорошая, запишем красивое видео!")

    return "\n".join(recommendations[:3])  # Максимум 3 рекомендации (закон малых чисел)
