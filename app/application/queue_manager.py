"""Очередь задач обработки видео (MVP, без внешней очереди)."""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import TEMP_DIR, MAX_CONCURRENT_JOBS, MAX_VIDEO_DURATION_SEC, MAX_VIDEO_SIZE_MB, MEDIA_UPLOAD_TIMEOUT
from app.video import VideoProcessor
from app.utils.video_validator import validate_video_file
from app.application.state import analysis_store

logger = logging.getLogger(__name__)


@dataclass
class VideoJob:
    chat_id: int
    user_id: int
    file_id: str
    file_unique_id: str
    status_message_id: int
    overlay_type: str = "full"


JOB_QUEUE: asyncio.Queue = asyncio.Queue()
WORKERS_STARTED = False


async def enqueue_job(job: VideoJob) -> int:
    await JOB_QUEUE.put(job)
    return JOB_QUEUE.qsize()


def start_queue_workers(application) -> None:
    global WORKERS_STARTED
    if WORKERS_STARTED:
        return
    worker_count = max(1, MAX_CONCURRENT_JOBS)
    for i in range(worker_count):
        application.create_task(_worker_loop(application, i + 1))
    WORKERS_STARTED = True
    logger.info(f"✅ Запущено воркеров очереди: {worker_count}")


async def _worker_loop(application, worker_id: int) -> None:
    logger.info(f"🔧 Очередь: воркер {worker_id} запущен")
    while True:
        job: VideoJob = await JOB_QUEUE.get()
        try:
            await _process_job(application, job, worker_id)
        except Exception as e:
            logger.error(f"Ошибка обработки job в воркере {worker_id}: {e}", exc_info=True)
        finally:
            JOB_QUEUE.task_done()


async def _process_job(application, job: VideoJob, worker_id: int) -> None:
    bot = application.bot
    chat_id = job.chat_id
    loop = asyncio.get_running_loop()

    async def _edit_status(text: str) -> None:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=job.status_message_id, text=text)
        except Exception:
            pass

    await _edit_status("🎯 Ваша очередь подошла. Скачиваю видео...")

    # Скачивание файла
    file = await bot.get_file(job.file_id, read_timeout=MEDIA_UPLOAD_TIMEOUT, write_timeout=MEDIA_UPLOAD_TIMEOUT)
    video_path = TEMP_DIR / f"video_{job.user_id}_{job.file_unique_id}.mp4"
    await file.download_to_drive(video_path)

    # Валидация видео
    is_valid, error_msg = validate_video_file(video_path)
    if not is_valid:
        await _edit_status(
            f"❌ Ошибка валидации видео\n\n{error_msg}\n\n"
            "💡 Попробуйте другое видео или свяжитесь с поддержкой: @climb_ai"
        )
        _safe_unlink(video_path)
        return

    # Проверка длительности
    import cv2
    cap = cv2.VideoCapture(str(video_path))
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS) or 1
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()
        duration_sec = frames / fps
        if duration_sec > MAX_VIDEO_DURATION_SEC:
            await _edit_status(
                f"❌ Видео длиннее {MAX_VIDEO_DURATION_SEC} секунд\n\n"
                f"📊 У вас: {duration_sec:.0f} с. Максимум: до 2 мин (120 с).\n\n"
                "💡 Обрежьте видео и отправьте снова."
            )
            _safe_unlink(video_path)
            return
    else:
        cap.release()

    await _edit_status("🎬 Начинаю полный анализ видео...\n⏳ Обычно 1–2 минуты (видео до 2 мин)")

    processor = VideoProcessor()

    def progress_callback(progress, stage):
        if progress % 20 == 0:
            try:
                asyncio.run_coroutine_threadsafe(
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=job.status_message_id,
                        text=(
                            "🎬 Обрабатываю видео...\n"
                            f"{'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%\n\n"
                            f"{stage}"
                        ),
                    ),
                    loop,
                )
            except Exception:
                pass

    # Обработка видео в фоне
    result = await asyncio.to_thread(
        processor.process_video,
        Path(video_path),
        job.overlay_type,
        progress_callback
    )

    # Уведление о готовности
    await _edit_status(
        "✨ Видео обработано!\n\n"
        f"📊 Кадров: {result.get('total_frames', 0)}\n"
        f"📈 Качество позы: {result.get('avg_pose_quality', 0):.1f}%\n"
        f"⚡ Интенсивность: {result.get('avg_motion_intensity', 0):.1f}\n"
        f"🚨 Падение: {'Да' if result.get('fall_detected') else 'Нет'}\n\n"
        "📹 Отправляю обработанное видео..."
    )

    # Отправляем видео
    video_caption = (
        "Паутинка техники:\n"
        "QF — Спокойные ноги (точность постановки стоп)\n"
        "HP — Положение таза (близко к стене, ноги работают)\n"
        "DM — Диагональная координация (противоположные руки-ноги)\n"
        "RR — Считывание маршрута (планирование перед лазанием)\n"
        "RT — Ритм (равномерность темпа движений)\n"
        "DC — Контроль динамики (точность бросков, стабилизация)\n"
        "GR — Плавность перехватов (мягкое отпускание зацепов)\n\n"
        "Кружочки = напряжение суставов (зелёный<30%, жёлтый<60%, оранжевый<80%, красный>80%)\n"
        "Справа вверху: Стабильность, Продуктивность, Экономичность, Баланс"
    )
    with open(result['processed_video_path'], 'rb') as video:
        await bot.send_video(
            chat_id=chat_id,
            video=video,
            caption=video_caption,
            write_timeout=MEDIA_UPLOAD_TIMEOUT,
        )

    # Отправляем дашборд
    dashboard_path_str = result.get('dashboard_path')
    if dashboard_path_str:
        dashboard_path_obj = Path(dashboard_path_str)
        if dashboard_path_obj.exists():
            with open(dashboard_path_obj, 'rb') as dashboard_file:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=dashboard_file,
                    caption="📊 Дашборд с метриками анализа",
                    write_timeout=MEDIA_UPLOAD_TIMEOUT,
                )

    # Сохраняем результат в памяти (MVP)
    analysis_store.set(chat_id, result)

    # Сообщение после анализа
    from app.bot.messages import ANALYSIS_COMPLETE_MESSAGE
    await bot.send_message(chat_id=chat_id, text=ANALYSIS_COMPLETE_MESSAGE)

    # Очистка временных файлов
    _safe_unlink(Path(result.get('processed_video_path', '')))
    _safe_unlink(Path(result.get('dashboard_path', '')))
    _safe_unlink(video_path)


def _safe_unlink(path: Path) -> None:
    try:
        if path and path.exists():
            path.unlink(missing_ok=True)
    except Exception:
        pass
