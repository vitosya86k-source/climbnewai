"""Обработчики команд Telegram бота"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from app.reports import ReportGenerator
from app.config import MAX_VIDEO_SIZE_MB
from app.application.queue_manager import VideoJob, enqueue_job
from app.application.state import analysis_store
from .keyboards import (
    get_main_keyboard,
    get_report_format_keyboard,
    get_next_actions_keyboard,
    get_theory_keyboard,
)
from .messages import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    ABOUT_MESSAGE,
    PRICING_MESSAGE,
    REPORT_SELECTION_MESSAGE,
    REPORT_READY_MESSAGE,
    ERROR_MESSAGE
)

logger = logging.getLogger(__name__)

# Очередь обрабатывается воркерами
SEEN_USERS: set[int] = set()

THEORY_TEXTS = {
    "theory_qf": (
        "🦶 <b>QF — Спокойные ноги (Quiet Feet)</b>\n\n"
        "<b>Что измеряет:</b> Сколько раз вы переставляете ногу на одной и той же зацепке.\n\n"
        "<b>Почему важно:</b> Каждая лишняя перестановка тратит энергию.\n\n"
        "<b>Как улучшить:</b>\n"
        "— Смотрите на зацепку до постановки ноги\n"
        "— Лезьте «беззвучно»\n"
        "— Тренируйте простой маршрут с фокусом на точности ног"
    ),
    "theory_hp": (
        "🦴 <b>HP — Положение таза</b>\n\n"
        "<b>Что измеряет:</b> Насколько близко таз к стене.\n\n"
        "<b>Почему важно:</b> Близкий таз разгружает руки и переносит вес на ноги.\n\n"
        "<b>Как улучшить:</b>\n"
        "— Прижимайте таз к стене\n"
        "— Разворачивайте бедро внутрь на движениях\n"
        "— Следите, чтобы не «висеть» на руках"
    ),
    "theory_dm": (
        "↗️ <b>DM — Диагональная координация</b>\n\n"
        "<b>Что измеряет:</b> Использование диагоналей: правая рука + левая нога и наоборот.\n\n"
        "<b>Почему важно:</b> Диагональ даёт устойчивость и меньше раскачки.\n\n"
        "<b>Как улучшить:</b>\n"
        "— Осознанно чередуйте диагонали\n"
        "— Замедляйтесь на простых трассах и контролируйте связки конечностей"
    ),
    "theory_rr": (
        "👁️ <b>RR — Считывание маршрута</b>\n\n"
        "<b>Что измеряет:</b> Планирование и паузы перед ключевыми движениями.\n\n"
        "<b>Почему важно:</b> Без плана растёт хаос и перерасход сил.\n\n"
        "<b>Как улучшить:</b>\n"
        "— Перед стартом прочитайте трассу 30–60 сек\n"
        "— Отмечайте точки отдыха и ключевые перехваты"
    ),
    "theory_rt": (
        "🎵 <b>RT — Равномерность темпа</b>\n\n"
        "<b>Что измеряет:</b> Стабильность ритма движений.\n\n"
        "<b>Почему важно:</b> Ровный ритм = лучше контроль и экономия энергии.\n\n"
        "<b>Как улучшить:</b>\n"
        "— Лезьте с счётом или под ритм\n"
        "— Избегайте серии резких судорожных движений"
    ),
    "theory_dc": (
        "💥 <b>DC — Контроль после бросков</b>\n\n"
        "<b>Что измеряет:</b> Точность и стабилизацию после динамических движений.\n\n"
        "<b>Почему важно:</b> На сложных трассах без контроля динамики много срывов.\n\n"
        "<b>Как улучшить:</b>\n"
        "— Тренируйте «поймал и замер»\n"
        "— После броска фиксируйте корпус 1 сек"
    ),
    "theory_gr": (
        "🤲 <b>GR — Плавность перехватов</b>\n\n"
        "<b>Что измеряет:</b> Насколько мягко отпускаете и берёте зацепки.\n\n"
        "<b>Почему важно:</b> Резкие перехваты перегружают пальцы и плечи.\n\n"
        "<b>Как улучшить:</b>\n"
        "— Делайте мягкий хват\n"
        "— Тренируйте траверс с фокусом на плавности"
    ),
    "theory_grade": (
        "🎯 <b>Как считается уровень</b>\n\n"
        "Уровень рассчитывается отдельно от общего балла техники:\n"
        "— 7 базовых метрик с весами\n"
        "— компенсация шума трекинга\n"
        "— бонус за сложность движений (динамика, плотность перехватов)\n\n"
        "Итог: уровень может быть выше/ниже общего балла — это нормально."
    ),
    "theory_scores": (
        "📊 <b>Что значат баллы</b>\n\n"
        "<b>Общий балл</b> — качество техники по 7 метрикам.\n"
        "<b>Уровень</b> — оценка сложности пролаза по отдельному алгоритму.\n\n"
        "Поэтому общий балл и уровень не обязаны совпадать."
    ),
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    logger.info(f"📥 Получена команда /start от пользователя {update.effective_user.id}")
    if update.effective_user:
        SEEN_USERS.add(update.effective_user.id)
    await _send_welcome(update)


async def _send_welcome(update: Update) -> None:
    if not update.message:
        return
    try:
        await update.message.reply_text(WELCOME_MESSAGE, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"❌ Ошибка отправки приветствия: {e}", exc_info=True)


async def _ensure_welcomed(update: Update) -> None:
    user = update.effective_user
    if not user or user.id in SEEN_USERS:
        return
    SEEN_USERS.add(user.id)
    await _send_welcome(update)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /help и кнопки Помощь"""
    await _ensure_welcomed(update)
    await update.message.reply_text(HELP_MESSAGE, parse_mode='HTML', reply_markup=get_main_keyboard())


async def theory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка/команда теории."""
    await _ensure_welcomed(update)
    await update.message.reply_text(
        "📖 <b>Теория метрик</b>\n\n"
        "Выберите метрику — что измеряет, почему важна и как улучшить.\n\n"
        "<i>Методология: Eric J. Hörst «Training for Climbing»</i>",
        parse_mode='HTML',
        reply_markup=get_theory_keyboard(),
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка/команда о боте."""
    await _ensure_welcomed(update)
    await update.message.reply_text(ABOUT_MESSAGE, parse_mode='HTML', reply_markup=get_main_keyboard())


async def send_video_prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подсказка как отправить видео."""
    await _ensure_welcomed(update)
    await update.message.reply_text(
        "📎 Нажмите скрепку внизу и выберите видео из галереи.\n\n"
        "Формат: MP4, MOV или AVI\n"
        "До 2 минут, до 100 МБ.",
        reply_markup=get_main_keyboard(),
    )


async def pricing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Тарифы"""
    await update.message.reply_text(PRICING_MESSAGE)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /progress и кнопки Мой прогресс"""
    user = update.effective_user
    
    try:
        await update.message.reply_text(
            "📊 Прогресс в MVP пока не сохраняется.\n\n"
            "Отправьте видео для нового анализа."
        )
    except Exception as e:
        logger.error(f"Ошибка в progress_command: {e}")
        await update.message.reply_text(ERROR_MESSAGE.format(error=str(e)))


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки видео"""
    await _ensure_welcomed(update)
    logger.info(f"📹 Получено видео от пользователя {update.effective_user.id}")
    user = update.effective_user
    message = update.message
    video_file = message.video or message.video_note
    if not video_file and message.document and message.document.mime_type and message.document.mime_type.startswith("video/"):
        video_file = message.document
    if not video_file:
        await message.reply_text("Не удалось распознать видеофайл.", reply_markup=get_main_keyboard())
        return
    
    try:
        logger.info(f"📹 Обработка видео: file_id={video_file.file_id}, size={video_file.file_size}")
        # Проверка размера
        file_size_mb = video_file.file_size / (1024 * 1024)
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            await update.message.reply_text(
                f"❌ Файл слишком большой!\n\n"
                f"📊 Ваш файл: {file_size_mb:.1f} МБ\n"
                f"📏 Максимум: {MAX_VIDEO_SIZE_MB} МБ\n\n"
                f"💡 Обрежьте видео или уменьшите качество"
            )
            return
        
        # Ставим в очередь
        status_msg = await update.message.reply_text("⏳ Принял видео. Ставлю в очередь...")

        position = await enqueue_job(
            VideoJob(
                chat_id=message.chat_id,
                user_id=user.id,
                file_id=video_file.file_id,
                file_unique_id=video_file.file_unique_id,
                status_message_id=status_msg.message_id,
                overlay_type="full"
            )
        )

        if position > 1:
            await status_msg.edit_text(
                f"⏳ Сейчас много запросов.\n"
                f"Ваше место в очереди: {position}\n\n"
                f"Примерное ожидание: ~{(position - 1) * 2} мин.\n"
                "Как только очередь дойдёт до вас — начну обработку."
            )
        else:
            await status_msg.edit_text("🎯 Ваша очередь подошла. Готовлю обработку...")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_video: {e}")
        error_msg = str(e)
        
        # Специальные сообщения для разных ошибок
        if "Timed out" in error_msg or "timeout" in error_msg.lower():
            await update.message.reply_text(
                "⏱️ Превышено время ожидания.\n\n"
                "Возможные причины: длинное видео, медленная сеть или загрузка.\n\n"
                "💡 Видео до 2 минут — в приоритете. Укоротите или повторите позже. "
                "Если проблема повторится — напишите в поддержку: @climb_ai"
            )
        else:
            await update.message.reply_text(ERROR_MESSAGE.format(error=error_msg))


async def handle_overlay_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора типа визуализации"""
    query = update.callback_query
    
    if not query:
        return

    # Безопасно отвечаем на callback (может быть устаревшим)
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback: {e}")
        return  # Прерываем обработку, если callback устарел

    data = query.data
    if not data:
        return

    # В MVP визуализации не выбираются — всегда полный анализ
    await query.edit_message_text(
        "🎯 Сейчас доступен только полный анализ.\n\n"
        "Отправьте видео для обработки."
    )


async def handle_theory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок теории."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    text = THEORY_TEXTS.get(query.data, "Раздел в разработке.")
    back_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ К списку", callback_data="theory_back")]]
    )
    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=back_keyboard,
    )


async def handle_theory_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к списку теории."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    await query.edit_message_text(
        "📖 <b>Теория метрик</b>\n\nВыберите метрику:",
        parse_mode='HTML',
        reply_markup=get_theory_keyboard(),
    )


async def handle_text_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Любой нераспознанный текст."""
    await _ensure_welcomed(update)
    if not update.message:
        return
    await update.message.reply_text(
        "📎 Нажмите «📹 Отправить видео» или отправьте видео через скрепку.\n"
        "Также доступна кнопка «📖 Теория».",
        reply_markup=get_main_keyboard(),
    )


# Обсуждение результатов с ИИ в этой версии отключено
# async def handle_discuss_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Обработчик обсуждения результатов с ИИ"""
#     ...
#     (см. историю коммитов для восстановления)


async def handle_report_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора формата отчета"""
    query = update.callback_query

    # Безопасно отвечаем на callback
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback: {e}")

    report_format = query.data.replace("report_", "")
    
    await query.edit_message_text("📝 Генерирую отчет...\n⏳ Это займет 10-20 секунд")
    
    try:
        # Генерируем отчет
        generator = ReportGenerator()
        analysis_result = analysis_store.get(query.message.chat_id)
        
        if not analysis_result:
            logger.error("❌ Нет данных анализа для генерации отчета")
            await query.edit_message_text(
                "❌ Ошибка: Нет данных анализа\n\n"
                "Пожалуйста, сначала обработайте видео с разметкой, "
                "а затем запросите отчет."
            )
            return
        
        user = update.effective_user
        
        report_data = await generator.generate_report(
            analysis_result,
            report_format,
            user.full_name or "Скалолаз"
        )
        
        # ВРЕМЕННО ОТКЛЮЧЕНО: Сохраняем отчет в БД
        # with get_session() as session:
        #     video_id = context.user_data.get('current_video_id')
        #     db_user = get_or_create_user(session, user.id, user.username, user.full_name)
        #     
        #     update_video_report(
        #         session,
        #         video_id,
        #         report_data['report_text'],
        #         report_format,
        #         report_data['expert_assigned'],
        #         report_data['expert_score'],
        #         report_data['neuro_type']
        #     )
        #     
        #     # Создаем запись прогресса
        #     create_progress_record(session, db_user.id, video_id, analysis_result)
        #     
        #     # Обновляем счетчик видео
        #     update_user_videos_count(session, db_user.id)
        
        # Отправляем отчет
        format_names = {
            'technical': '📊 Технический',
            'client': '😊 Клиентский',
            'detective': '🕵️ Детектив',
            'gamer': '🎮 Геймерский',
            'coach': '👨‍🎓 Тренерский',
            'girl_style': '💃 Girl Style',
            'beginner': '💪 Для новичка',
            'random': '🎲 Рандомный'
        }
        
        # Разбиваем длинный отчет на части если нужно
        report_text = report_data['report_text']
        max_length = 4000
        
        if len(report_text) <= max_length:
            await query.edit_message_text(
                REPORT_READY_MESSAGE.format(
                    report_format=format_names.get(report_format, report_format),
                    report_text=report_text
                )
            )
        else:
            # Отправляем по частям
            await query.edit_message_text(
                f"📑 ВАШ ПОЛНЫЙ АНАЛИЗ ({format_names.get(report_format, report_format)})\n\n"
                "Отчет слишком большой, отправляю по частям..."
            )
            
            parts = [report_text[i:i+max_length] for i in range(0, len(report_text), max_length)]
            for i, part in enumerate(parts, 1):
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"📄 Часть {i}/{len(parts)}:\n\n{part}"
                )
        
        # Показываем следующие действия
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Что дальше?",
            reply_markup=get_next_actions_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        await query.edit_message_text(ERROR_MESSAGE.format(error=str(e)))


async def handle_next_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик действий после получения результата"""
    query = update.callback_query

    # Безопасно отвечаем на callback
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback: {e}")

    action = query.data.replace("action_", "")
    
    # Обсуждение результатов с ИИ в этой версии отключено
    # if action == "discuss_with_ai":
    #     await handle_discuss_with_ai(update, context)
    #     return

    if action == "another_overlay":
        # Эта функция больше не используется - всегда полный анализ
        await query.edit_message_text(
            "🎯 Всегда используется полный анализ.\n\n"
            "Отправьте новое видео для анализа."
        )
        return
    
    elif action == "generate_report":
        # Перейти к генерации отчета
        await query.edit_message_text(
            REPORT_SELECTION_MESSAGE,
            reply_markup=get_report_format_keyboard()
        )
    
    elif action == "another_report":
        await query.edit_message_text(
            REPORT_SELECTION_MESSAGE,
            reply_markup=get_report_format_keyboard()
        )
    
    elif action == "new_video":
        await query.edit_message_text(
            "📹 Готов к новому анализу!\n\n"
            "Отправь следующее видео."
        )
    
    elif action == "progress":
        await progress_command(update, context)


def setup_handlers(application):
    """Настройка всех обработчиков"""
    logger.info("🔧 Настройка обработчиков...")
    
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    logger.info("✅ Обработчик /start зарегистрирован")
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("theory", theory_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Кнопки главного меню
    application.add_handler(MessageHandler(
        filters.Text(["📹 Отправить видео"]),
        send_video_prompt_command
    ))
    application.add_handler(MessageHandler(
        filters.Text(["❓ Помощь", "Помощь", "/help"]),
        help_command
    ))
    application.add_handler(MessageHandler(
        filters.Text(["📖 Теория"]),
        theory_command
    ))
    application.add_handler(MessageHandler(
        filters.Text(["ℹ️ О боте"]),
        about_command
    ))
    
    # Видео (video, video_note, документ-видео)
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video))
    application.add_handler(MessageHandler(filters.Document.VIDEO, handle_video))
    
    # Callback queries
    application.add_handler(CallbackQueryHandler(
        handle_theory_back,
        pattern="^theory_back$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_theory_callback,
        pattern="^theory_"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_overlay_selection,
        pattern="^overlay_"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_report_selection,
        pattern="^report_"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_next_actions,
        pattern="^action_"
    ))

    # Фолбэк для любого текста
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_fallback
    ))
    
    logger.info("Все обработчики настроены")
