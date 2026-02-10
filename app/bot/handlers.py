"""Обработчики команд Telegram бота"""

import logging
from telegram import Update
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
    get_overlay_selection_keyboard,
    get_report_format_keyboard,
    get_next_actions_keyboard
)
from .messages import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    PRICING_MESSAGE,
    VIDEO_READY_MESSAGE,
    REPORT_SELECTION_MESSAGE,
    REPORT_READY_MESSAGE,
    ERROR_MESSAGE
)

logger = logging.getLogger(__name__)

# Очередь обрабатывается воркерами


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    logger.info(f"📥 Получена команда /start от пользователя {update.effective_user.id}")
    user = update.effective_user
    
    try:
        # MVP: без БД, просто отправляем приветствие
        welcome_text = WELCOME_MESSAGE
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в start_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(ERROR_MESSAGE.format(error=str(e)))
        except Exception as e2:
            logger.error(f"❌ Не удалось отправить сообщение об ошибке: {e2}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /help и кнопки Помощь"""
    await update.message.reply_text(HELP_MESSAGE)


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
    logger.info(f"📹 Получено видео от пользователя {update.effective_user.id}")
    user = update.effective_user
    video_file = update.message.video
    
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
                chat_id=update.message.chat_id,
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
    
    # Кнопки главного меню (только помощь для MVP)
    application.add_handler(MessageHandler(
        filters.Text(["❓ Помощь", "Помощь", "/help"]),
        help_command
    ))
    
    # Видео
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    # Callback queries
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
    
    logger.info("Все обработчики настроены")
