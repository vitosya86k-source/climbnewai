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



    if pose_quality < 50:
        recommendations.append("🕸️ **Метрики** - техника требует внимания, посмотри на паутинку")

    if motion_intensity < 30:
        recommendations.append("⏱️ **Скорость** - много думаешь на трассе, проверь карту решений")

    if not recommendations:
        recommendations.append("🎯 **Полный анализ** - техника хорошая, запишем красивое видео!")

    return "\n".join(recommendations[:3])  # Максимум 3 рекомендации (закон малых чисел)
