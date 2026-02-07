"""Обработчики команд Telegram бота"""

import logging
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from app.database import get_session
from app.database.crud import (
    get_or_create_user,
    can_analyze_video,
    update_user_videos_count,
    create_video,
    update_video_analysis,
    update_video_report,
    create_progress_record,
    create_video_export,
    get_user_videos
)
from app.video import VideoProcessor
from app.reports import ReportGenerator
from app.config import TEMP_DIR, FREE_VIDEO_LIMIT, MAX_VIDEO_SIZE_MB, MAX_VIDEO_DURATION_SEC, MEDIA_UPLOAD_TIMEOUT
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
    NO_VIDEOS_LEFT_MESSAGE,
    ERROR_MESSAGE
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    logger.info(f"📥 Получена команда /start от пользователя {update.effective_user.id}")
    user = update.effective_user
    
    try:
        logger.info(f"🔍 Создание/получение пользователя в БД: telegram_id={user.id}")
        with get_session() as session:
            db_user = get_or_create_user(
                session,
                telegram_id=user.id,
                username=user.username,
                name=user.full_name
            )
            
            logger.info(f"✅ Пользователь получен: id={db_user.id}, free_videos_left={db_user.free_videos_left}")
            
            # Убрана информация о бесплатных видео для MVP
            welcome_text = WELCOME_MESSAGE
            
            logger.info(f"📤 Отправка приветственного сообщения пользователю {user.id}")
            await update.message.reply_text(
                welcome_text,
                reply_markup=get_main_keyboard()
            )
            logger.info(f"✅ Приветственное сообщение отправлено")
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
        with get_session() as session:
            db_user = get_or_create_user(session, user.id, user.username, user.full_name)
            videos = get_user_videos(session, db_user.id, limit=5)
            
            if not videos:
                await update.message.reply_text(
                    "📊 У тебя пока нет проанализированных видео.\n\n"
                    "Отправь свое первое видео для анализа!"
                )
                return
            
            response = f"📊 ТВОЙ ПРОГРЕСС\n\n"
            response += f"Всего видео: {db_user.videos_analyzed}\n"
            response += f"Осталось бесплатных: {db_user.free_videos_left}\n\n"
            response += "🎬 ПОСЛЕДНИЕ ВИДЕО:\n\n"
            
            for i, video in enumerate(videos, 1):
                response += f"{i}. Качество: {video.avg_pose_quality:.1f}%"
                if video.fall_detected:
                    response += " 🚨"
                response += f"\n   Эксперт: {video.expert_assigned}\n"
                response += f"   Нейротип: {video.neuro_type}\n\n"
            
            await update.message.reply_text(response)
    
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
        # Проверка лимита
        with get_session() as session:
            db_user = get_or_create_user(session, user.id, user.username, user.full_name)
            
            if not can_analyze_video(session, db_user.id):
                await update.message.reply_text(
                    NO_VIDEOS_LEFT_MESSAGE.format(videos_count=db_user.videos_analyzed)
                )
                return
            
            # Сохраняем user_id для использования вне сессии
            user_db_id = db_user.id
        
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
        
        # Скачиваем видео (длинный таймаут на скачивание и загрузку)
        status_msg = await update.message.reply_text("⏳ Скачиваю видео...")
        
        file = await context.bot.get_file(
            video_file.file_id,
            read_timeout=MEDIA_UPLOAD_TIMEOUT,
            write_timeout=MEDIA_UPLOAD_TIMEOUT,
        )
        video_path = TEMP_DIR / f"video_{user.id}_{video_file.file_unique_id}.mp4"
        await file.download_to_drive(video_path)
        
        logger.info(f"Видео скачано: {video_path}")
        
        # Валидация видеофайла (защита от DoS и битых файлов)
        from app.utils.video_validator import validate_video_file
        
        is_valid, error_msg = validate_video_file(video_path)
        if not is_valid:
            await status_msg.edit_text(
                f"❌ Ошибка валидации видео\n\n"
                f"{error_msg}\n\n"
                f"💡 Попробуйте другое видео или свяжитесь с поддержкой: @climb_ai"
            )
            # Удаляем битый файл
            try:
                video_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Не удалось удалить битый файл: {e}")
            return
        
        # Проверка длительности (до 2 мин = 120 с)
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 1
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            duration_sec = frames / fps
            if duration_sec > MAX_VIDEO_DURATION_SEC:
                await status_msg.edit_text(
                    f"❌ Видео длиннее {MAX_VIDEO_DURATION_SEC} секунд\n\n"
                    f"📊 У вас: {duration_sec:.0f} с. Максимум: до 2 мин (120 с).\n\n"
                    "💡 Обрежьте видео и отправьте снова."
                )
                return
        else:
            cap.release()
        
        # ВРЕМЕННО ОТКЛЮЧЕНО: Сохраняем в БД
        # with get_session() as session:
        #     db_video = create_video(session, user_db_id, video_file.file_id)
        #     context.user_data['current_video_id'] = db_video.id
        context.user_data['video_path'] = str(video_path)
        
        # Сразу начинаем обработку с полным анализом (без выбора визуализации)
        context.user_data['selected_overlay'] = 'full'
        await status_msg.edit_text("🎯 Начинаю полный анализ видео...\n⏳ Обычно 1–2 минуты (видео до 2 мин)")
        
        # Запускаем обработку сразу
        processor = VideoProcessor()
        
        async def progress_callback(progress, stage):
            if progress % 20 == 0:
                try:
                    await status_msg.edit_text(
                        f"🎬 Обрабатываю видео...\n"
                        f"{'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%\n\n"
                        f"{stage}"
                    )
                except:
                    pass
        
        try:
            result = await processor.process_video(
                Path(video_path),
                'full',
                progress_callback
            )
            
            logger.info(f"Видео обработано: {result['processed_video_path']}")
            
            await status_msg.edit_text(
                VIDEO_READY_MESSAGE.format(
                    total_frames=result['total_frames'],
                    avg_quality=result['avg_pose_quality'],
                    avg_intensity=result['avg_motion_intensity'],
                    fall_detected="Да 🚨" if result['fall_detected'] else "Нет"
                )
            )
            
            # Отправляем видео с краткой легендой на русском (Telegram ограничение ~1024 символа)
            video_caption = """Паутинка техники:
QF — Спокойные ноги (точность постановки стоп)
HP — Положение таза (близко к стене, ноги работают)
DM — Диагональная координация (противоположные руки-ноги)
RR — Считывание маршрута (планирование перед лазанием)
RT — Ритм (равномерность темпа движений)
DC — Контроль динамики (точность бросков, стабилизация)
GR — Плавность перехватов (мягкое отпускание зацепов)

Кружочки = напряжение суставов (зелёный<30%, жёлтый<60%, оранжевый<80%, красный>80%)
Справа вверху: Стабильность, Продуктивность, Экономичность, Баланс"""
            
            with open(result['processed_video_path'], 'rb') as video:
                await context.bot.send_video(
                    chat_id=update.message.chat_id,
                    video=video,
                    caption=video_caption,
                    write_timeout=MEDIA_UPLOAD_TIMEOUT,
                )
            
            # Отправляем дашборд
            dashboard_path_str = result.get('dashboard_path')
            # #region agent log
            with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                import json as _json
                f.write(_json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"H-D","location":"handlers.py:handle_video:dashboard_check","message":"Dashboard path check","data":{"dashboard_path":dashboard_path_str,"result_keys":list(result.keys()) if result else []},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            logger.info(f"Проверка дашборда: dashboard_path={dashboard_path_str}")
            if dashboard_path_str:
                dashboard_path_obj = Path(dashboard_path_str)
                logger.info(f"Дашборд существует: {dashboard_path_obj.exists()}, размер: {dashboard_path_obj.stat().st_size if dashboard_path_obj.exists() else 0}")
                if dashboard_path_obj.exists():
                    try:
                        with open(dashboard_path_obj, 'rb') as dashboard_file:
                            await context.bot.send_photo(
                                chat_id=update.message.chat_id,
                                photo=dashboard_file,
                                caption="📊 Дашборд с метриками анализа",
                                write_timeout=MEDIA_UPLOAD_TIMEOUT,
                            )
                        logger.info("✅ Дашборд успешно отправлен пользователю")
                    except Exception as e:
                        logger.error(f"❌ Не удалось отправить дашборд: {e}", exc_info=True)
                else:
                    logger.warning(f"⚠️ Файл дашборда не существует: {dashboard_path_obj}")
            else:
                logger.warning("⚠️ dashboard_path отсутствует в результате")
            
            # Сохраняем результат (обсуждение с ИИ в этой версии отключено)
            context.user_data['analysis_result'] = result
            
            # Сообщение после анализа без кнопки «Обсудить с ИИ»
            from app.bot.messages import ANALYSIS_COMPLETE_MESSAGE
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=ANALYSIS_COMPLETE_MESSAGE
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки видео: {e}", exc_info=True)
            error_msg = str(e)
            if "Timed out" in error_msg or "timeout" in error_msg.lower():
                await status_msg.edit_text(
                    "⏱️ Превышено время ожидания\n\n"
                    "Возможные причины: длинное видео, медленная сеть или загрузка.\n\n"
                    "💡 Попробуйте укоротить видео (до 2 мин) или повторить позже. "
                    "Если проблема повторится — напишите в поддержку: @climb_ai"
                )
            else:
                await status_msg.edit_text(ERROR_MESSAGE.format(error=error_msg))
        
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

    if data == "overlay_done":
        # Проверяем наличие видео
        video_path_str = context.user_data.get('video_path')
        if not video_path_str:
            await query.edit_message_text(
                "❌ Видео не найдено!\n\n"
                "Сначала отправьте видео для анализа, затем выберите тип визуализации."
            )
            return

        # Начинаем обработку
        overlay_type = context.user_data.get('selected_overlay', 'skeleton')
        video_path = Path(video_path_str)
        
        await query.edit_message_text("🎬 Начинаю обработку видео...\n⏳ Обычно 1–2 минуты (видео до 2 мин)")
        
        try:
            # Обрабатываем видео
            processor = VideoProcessor()
            
            async def progress_callback(progress, stage):
                if progress % 20 == 0:  # Обновляем каждые 20%
                    try:
                        await query.edit_message_text(
                            f"🎬 Обрабатываю видео...\n"
                            f"{'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%\n\n"
                            f"{stage}"
                        )
                    except:
                        pass  # Игнорируем ошибки редактирования
            
            result = await processor.process_video(
                video_path,
                overlay_type,
                progress_callback
            )
            
            logger.info(f"Видео обработано: {result['processed_video_path']}")
            
            # ВРЕМЕННО ОТКЛЮЧЕНО: Сохраняем результат в БД
            # with get_session() as session:
            #     video_id = context.user_data['current_video_id']
            #     db_video = update_video_analysis(
            #         session,
            #         video_id,
            #         result,
            #         result['csv_path']
            #     )
            #     
            #     # Создаем запись экспорта
            #     processed_video = Path(result['processed_video_path'])
            #     create_video_export(
            #         session,
            #         video_id,
            #         overlay_type,
            #         telegram_file_id="local"  # Пока локально, потом загрузим в Telegram
            #     )
            
            # Отправляем результат
            await query.edit_message_text(
                VIDEO_READY_MESSAGE.format(
                    total_frames=result['total_frames'],
                    avg_quality=result['avg_pose_quality'],
                    avg_intensity=result['avg_motion_intensity'],
                    fall_detected="Да 🚨" if result['fall_detected'] else "Нет"
                )
            )
            
            # Отправляем видео
            overlay_names = {
                # 5 ключевых визуализаций v3.0
                'full': '🎯 Полный анализ',
                'spider_metrics': '🕸️ Метрики',
                'weight_load': '⚖️ Нагрузка (кг)',
                'tension_zones': '⚠️ Зажимы',
                'speed_map': '⏱️ Скорость',
                'ideal_ghost': '👻 Призрак-эталон',
            }

            # Формируем простую подпись без легенд
            caption = f"🎬 Обработанное видео: {overlay_names.get(overlay_type, overlay_type)}"
            
            with open(result['processed_video_path'], 'rb') as video:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=video,
                    caption=caption,
                    write_timeout=MEDIA_UPLOAD_TIMEOUT,
                )
            
            # CSV отключен (слишком большой файл)
            # with open(result['csv_path'], 'rb') as csv_file:
            #     await context.bot.send_document(
            #         chat_id=query.message.chat_id,
            #         document=csv_file,
            #         caption="📊 CSV с покадровым анализом"
            #     )
            
            # Отправляем дашборд, если он создан
            if result.get('dashboard_path') and Path(result['dashboard_path']).exists():
                try:
                    with open(result['dashboard_path'], 'rb') as dashboard_file:
                        await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=dashboard_file,
                            caption="📊 Дашборд с метриками анализа",
                            write_timeout=MEDIA_UPLOAD_TIMEOUT,
                        )
                    logger.info("Дашборд отправлен пользователю")
                except Exception as e:
                    logger.warning(f"Не удалось отправить дашборд: {e}")
            
            # Сохраняем результат (обсуждение с ИИ в этой версии отключено)
            context.user_data['analysis_result'] = result
            
            # Сообщение после анализа без кнопки «Обсудить с ИИ»
            from app.bot.messages import ANALYSIS_COMPLETE_MESSAGE
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=ANALYSIS_COMPLETE_MESSAGE
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки видео: {e}")
            error_msg = str(e)
            
            if "Timed out" in error_msg or "timeout" in error_msg.lower():
                await query.edit_message_text(
                    "⏱️ Превышено время обработки.\n\n"
                    "Видео до 2 минут обрабатываются в приоритете. Укоротите или напишите в поддержку: @climb_ai"
                )
            elif "center_of_mass" in error_msg:
                await query.edit_message_text(
                    "❌ Ошибка анализа движения\n\n"
                    "Не удалось определить центр масс.\n\n"
                    "💡 Возможные причины:\n"
                    "• Человек плохо виден в кадре\n"
                    "• Слишком быстрые движения\n"
                    "• Плохое освещение\n\n"
                    "Попробуйте другое видео с лучшей видимостью"
                )
            else:
                await query.edit_message_text(ERROR_MESSAGE.format(error=error_msg))
    
    elif data == "overlay_show_more" or data == "overlay_show_main":
        # Эти функции больше не используются - всегда полный анализ
        await query.edit_message_text(
            "🎯 Всегда используется полный анализ.\n\n"
            "Отправьте новое видео для анализа."
        )
        return

    else:
        # Все остальные типы визуализации больше не поддерживаются
        # Перенаправляем на полный анализ
        await query.edit_message_text(
            "🎯 Всегда используется полный анализ.\n\n"
            "Отправьте новое видео для анализа."
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
        analysis_result = context.user_data.get('analysis_result')
        
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


