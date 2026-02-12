"""Клавиатуры для Telegram бота с BoulderVision"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная закрепленная клавиатура."""
    keyboard = [
        ["📹 Отправить видео", "❓ Помощь"],
        ["📖 Теория", "ℹ️ О боте"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


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


def get_theory_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура теории по метрикам."""
    keyboard = [
        [InlineKeyboardButton("🦶 QF — Спокойные ноги", callback_data="theory_qf")],
        [InlineKeyboardButton("🦴 HP — Положение таза", callback_data="theory_hp")],
        [InlineKeyboardButton("↗️ DM — Диагональная координация", callback_data="theory_dm")],
        [InlineKeyboardButton("👁️ RR — Считывание маршрута", callback_data="theory_rr")],
        [InlineKeyboardButton("🎵 RT — Ритм движений", callback_data="theory_rt")],
        [InlineKeyboardButton("💥 DC — Контроль динамики", callback_data="theory_dc")],
        [InlineKeyboardButton("🤲 GR — Плавность перехватов", callback_data="theory_gr")],
        [InlineKeyboardButton("🎯 Как считается уровень", callback_data="theory_grade")],
        [InlineKeyboardButton("📊 Что значат баллы", callback_data="theory_scores")],
    ]
    return InlineKeyboardMarkup(keyboard)
