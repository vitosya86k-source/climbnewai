"""Очередь задач обработки видео (MVP, без внешней очереди)."""

import asyncio
import gc
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from telegram.error import NetworkError

from app.config import (
    TEMP_DIR,
    MAX_CONCURRENT_JOBS,
    MAX_VIDEO_DURATION_SEC,
    MAX_VIDEO_SIZE_MB,
    MEDIA_UPLOAD_TIMEOUT,
    TELEGRAM_MAX_SEND_VIDEO_MB,
    PROCESSING_TIMEOUT_SEC,
)
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
PROCESSING_SEMAPHORE = asyncio.Semaphore(1)
WORKER_TASKS: list[asyncio.Task] = []


async def enqueue_job(job: VideoJob) -> int:
    await JOB_QUEUE.put(job)
    return JOB_QUEUE.qsize()


def start_queue_workers(application) -> None:
    global WORKERS_STARTED
    if WORKERS_STARTED:
        return
    worker_count = max(1, MAX_CONCURRENT_JOBS)
    for i in range(worker_count):
        # post_init вызывается до полного старта Application, поэтому запускаем задачи через asyncio.
        # Остановку делаем вручную в stop_queue_workers().
        task = asyncio.create_task(_worker_loop(application, i + 1))
        WORKER_TASKS.append(task)
    WORKERS_STARTED = True
    logger.info(f"✅ Запущено воркеров очереди: {worker_count}")


async def stop_queue_workers() -> None:
    """Корректная остановка воркеров при shutdown."""
    global WORKERS_STARTED
    if not WORKER_TASKS:
        WORKERS_STARTED = False
        return
    for task in WORKER_TASKS:
        task.cancel()
    await asyncio.gather(*WORKER_TASKS, return_exceptions=True)
    WORKER_TASKS.clear()
    WORKERS_STARTED = False


async def _worker_loop(application, worker_id: int) -> None:
    logger.info(f"🔧 Очередь: воркер {worker_id} запущен")
    try:
        while True:
            job: VideoJob = await JOB_QUEUE.get()
            try:
                await asyncio.wait_for(
                    _process_job(application, job, worker_id),
                    timeout=PROCESSING_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Таймаут обработки job в воркере {worker_id} (> {PROCESSING_TIMEOUT_SEC}s)",
                    exc_info=True
                )
                try:
                    await application.bot.send_message(
                        chat_id=job.chat_id,
                        text=(
                            "⏰ Обработка заняла слишком много времени.\n\n"
                            "Попробуйте более короткое видео (до 1 минуты) или отправьте повторно."
                        ),
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Ошибка обработки job в воркере {worker_id}: {e}", exc_info=True)
            finally:
                # Явно освобождаем память после каждой задачи.
                gc.collect()
                JOB_QUEUE.task_done()
    except asyncio.CancelledError:
        logger.info(f"🛑 Воркер {worker_id} остановлен")
        raise


async def _process_job(application, job: VideoJob, worker_id: int) -> None:
    async with PROCESSING_SEMAPHORE:
        bot = application.bot
        chat_id = job.chat_id
        loop = asyncio.get_running_loop()
        video_path: Optional[Path] = None
        result: Optional[dict] = None

        async def _edit_status(text: str) -> None:
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=job.status_message_id, text=text)
            except Exception:
                pass

        try:
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
                return

            # Проверка длительности
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
                    return
            else:
                cap.release()

            await _edit_status("🎬 Начинаю полный анализ видео...\n⏳ Обычно 1–2 минуты (видео до 2 мин)")

            processor = VideoProcessor()

            last_sent_progress = -1
            last_status_update_monotonic = 0.0

            def progress_callback(progress, stage):
                nonlocal last_sent_progress, last_status_update_monotonic
                if progress is None:
                    try:
                        logger.info(f"Worker {worker_id} stage: {stage}")
                        asyncio.run_coroutine_threadsafe(
                            bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=job.status_message_id,
                                text=(
                                    "🎬 Обрабатываю видео...\n"
                                    f"{stage}"
                                ),
                            ),
                            loop,
                        )
                    except Exception:
                        pass
                    return

                progress_int = max(0, min(100, int(progress)))
                now = time.monotonic()
                should_update = (
                    progress_int <= 20
                    or progress_int - last_sent_progress >= 5
                    or now - last_status_update_monotonic >= 20
                    or progress_int == 100
                )

                if should_update:
                    last_sent_progress = progress_int
                    last_status_update_monotonic = now
                    try:
                        logger.info(
                            f"Worker {worker_id} progress: {progress_int}% | stage: {stage}"
                        )
                        asyncio.run_coroutine_threadsafe(
                            bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=job.status_message_id,
                                text=(
                                    "🎬 Обрабатываю видео...\n"
                                    f"{'█' * (progress_int // 10)}{'░' * (10 - progress_int // 10)} {progress_int}%\n\n"
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
            processed_video_path = Path(result["processed_video_path"])
            sent_video_ok = await _send_result_video_with_fallback(
                bot=bot,
                chat_id=chat_id,
                status_message_id=job.status_message_id,
                video_path=processed_video_path,
                caption=video_caption,
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
            await bot.send_message(
                chat_id=chat_id,
                text=ANALYSIS_COMPLETE_MESSAGE if sent_video_ok else (
                    "✅ Анализ завершён.\n\n"
                    "Видео с оверлеем не удалось отправить из-за лимита Telegram по размеру файла.\n"
                    "Дашборд и расчёты сформированы."
                ),
            )
        except Exception as e:
            logger.error(f"Ошибка обработки для {chat_id}: {e}", exc_info=True)
            await _edit_status(
                "❌ Произошла ошибка при обработке видео.\n\n"
                "Попробуйте ещё раз или отправьте видео покороче."
            )
            raise
        finally:
            if result:
                _safe_unlink(Path(result.get('processed_video_path', '')))
                _safe_unlink(Path(result.get('dashboard_path', '')))
            if video_path:
                _safe_unlink(video_path)


def _safe_unlink(path: Path) -> None:
    try:
        if path and path.exists():
            path.unlink(missing_ok=True)
    except Exception:
        pass


def _file_size_mb(path: Path) -> float:
    try:
        if not path.exists():
            return float("inf")
        return path.stat().st_size / (1024 * 1024)
    except Exception:
        return float("inf")


def _try_compress_video_for_telegram(input_path: Path, max_mb: int) -> Optional[Path]:
    """
    Сжимает видео для отправки в Telegram.
    Возвращает путь к сжатому файлу, если он в лимите; иначе None.
    """
    # Сжимаем через ffmpeg (стабильный mp4 для Telegram)
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if not ffmpeg_bin or not ffprobe_bin:
        logger.warning("ffmpeg/ffprobe not found; skip compression")
        return None
    output_path = input_path.with_name(f"{input_path.stem}_tg.mp4")
    output_small = input_path.with_name(f"{input_path.stem}_tg_720.mp4")
    try:
        probe = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(input_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 60.0
        duration = max(1.0, duration)
        target_bitrate = int((max_mb * 8 * 1024 * 1024) / duration * 0.9)
        target_bitrate = min(target_bitrate, 4_000_000)

        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                str(input_path),
                "-c:v",
                "libx264",
                "-b:v",
                str(target_bitrate),
                "-maxrate",
                str(int(target_bitrate * 1.2)),
                "-bufsize",
                str(int(target_bitrate * 2)),
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "main",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            capture_output=True,
            check=False,
            timeout=180,
        )
        if _file_size_mb(output_path) <= float(max_mb) and _is_playable_video(output_path, ffprobe_bin):
            return output_path

        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                str(input_path),
                "-vf",
                "scale=-2:720",
                "-c:v",
                "libx264",
                "-b:v",
                str(max(400_000, target_bitrate // 2)),
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "main",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(output_small),
            ],
            capture_output=True,
            check=False,
            timeout=180,
        )
        if _file_size_mb(output_small) <= float(max_mb) and _is_playable_video(output_small, ffprobe_bin):
            _safe_unlink(output_path)
            return output_small
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg compression timeout reached")
    except Exception:
        logger.exception("Compression failed")
    _safe_unlink(output_path)
    _safe_unlink(output_small)
    return None


def _is_playable_video(path: Path, ffprobe_bin: str) -> bool:
    """Проверка, что файл реально читается и содержит видеопоток."""
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        proc = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height",
                "-of",
                "default=noprint_wrappers=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return proc.returncode == 0 and "codec_name=" in proc.stdout
    except Exception:
        return False


async def _send_result_video_with_fallback(
    bot,
    chat_id: int,
    status_message_id: int,
    video_path: Path,
    caption: str,
) -> bool:
    """
    Пытается отправить видео; при 413 пробует сжать и отправить повторно.
    Возвращает True, если хотя бы одна отправка видео успешна.
    """
    candidate = video_path
    tmp_compressed: Optional[Path] = None

    if _file_size_mb(candidate) > float(TELEGRAM_MAX_SEND_VIDEO_MB):
        tmp_compressed = _try_compress_video_for_telegram(candidate, TELEGRAM_MAX_SEND_VIDEO_MB)
        if tmp_compressed:
            candidate = tmp_compressed

    try:
        with open(candidate, "rb") as video:
            await bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=caption,
                write_timeout=MEDIA_UPLOAD_TIMEOUT,
            )
        return True
    except NetworkError as e:
        error_text = str(e)
        is_413 = "413" in error_text or "Request Entity Too Large" in error_text
        if not is_413:
            raise

        # Если 413 даже после предварительной проверки — пробуем сжать и отправить ещё раз.
        if tmp_compressed is None:
            tmp_compressed = _try_compress_video_for_telegram(video_path, TELEGRAM_MAX_SEND_VIDEO_MB)
            if tmp_compressed:
                try:
                    with open(tmp_compressed, "rb") as video:
                        await bot.send_video(
                            chat_id=chat_id,
                            video=video,
                            caption=caption,
                            write_timeout=MEDIA_UPLOAD_TIMEOUT,
                        )
                    return True
                except NetworkError as e2:
                    if "413" not in str(e2) and "Request Entity Too Large" not in str(e2):
                        raise

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_message_id,
            text=(
                "✅ Анализ выполнен, но Telegram отклонил отправку видео (слишком большой файл).\n\n"
                "Отправляю дашборд и итоговые метрики."
            ),
        )
        return False
    finally:
        if tmp_compressed:
            _safe_unlink(tmp_compressed)
