"""Главный файл запуска ClimbAI Telegram Bot"""

import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Патч библиотеки: при загрузке файлов не подставлять 20 сек, а использовать наш write_timeout
def _patch_telegram_media_timeout():
    from telegram.request import HTTPXRequest
    from telegram.request._baserequest import DefaultValue
    _orig_do = HTTPXRequest.do_request

    async def _do_request(self, url, method, request_data=None, read_timeout=DefaultValue,
                          write_timeout=DefaultValue, connect_timeout=DefaultValue, pool_timeout=DefaultValue):
        # При загрузке файлов использовать таймаут из клиента (мы задали 1200), а не 20 сек
        if isinstance(write_timeout, DefaultValue):
            write_timeout = self._client.timeout.write
        return await _orig_do(self, url, method, request_data, read_timeout,
                              write_timeout, connect_timeout, pool_timeout)

    HTTPXRequest.do_request = _do_request

_patch_telegram_media_timeout()

import logging
from telegram.ext import Application

from app.config import TELEGRAM_BOT_TOKEN
from app.database import init_db
from app.bot import setup_handlers
from app.utils import setup_logger

# Настройка логирования
logger = setup_logger("climbai", logging.INFO)

# Проверка Claude при старте отключена — в этой версии ИИ не используется для обсуждения
# async def test_claude_on_startup(): ...


async def post_init(application: Application) -> None:
    """Инициализация после создания приложения"""
    logger.info("🚀 Инициализация бота...")
    
    # Инициализация базы данных
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise
    
    logger.info("✅ Бот готов к работе!")


async def post_shutdown(application: Application) -> None:
    """Действия при остановке бота"""
    logger.info("🛑 Остановка бота...")


async def error_handler(update, context) -> None:
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка при обработке: {context.error}", exc_info=context.error)

    # Пытаемся уведомить пользователя
    try:
        if update and update.effective_message:
            error_text = str(context.error)

            # Специальные сообщения для известных ошибок
            if "Query is too old" in error_text:
                # Устаревший callback - игнорируем, уже обработано
                return
            elif "video_path" in error_text or "KeyError" in error_text:
                await update.effective_message.reply_text(
                    "❌ Сессия устарела\n\n"
                    "Пожалуйста, загрузите видео заново."
                )
            else:
                await update.effective_message.reply_text(
                    f"❌ Произошла ошибка\n\n"
                    f"Попробуйте ещё раз или напишите /start"
                )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")


def main():
    """Главная функция запуска"""
    logger.info("=" * 60)
    logger.info("🎯 ClimbAI Telegram Bot v2.0")
    logger.info("=" * 60)
    
    try:
        # Создаем приложение с увеличенными таймаутами
        from telegram.request import HTTPXRequest
        
        # Таймауты: отправка обработанного видео в Telegram может быть долгой (большой файл)
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=30.0,
            read_timeout=600.0,
            write_timeout=1200.0,     # 20 минут на загрузку видео в Telegram
            pool_timeout=30.0
        )
        
        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .request(request)
            .post_init(post_init)
            .post_shutdown(post_shutdown)
            .build()
        )
        
        # Настраиваем обработчики
        logger.info("🔧 Вызов setup_handlers...")
        setup_handlers(application)
        logger.info("✅ Обработчики настроены")

        # Глобальный обработчик ошибок
        application.add_error_handler(error_handler)
        logger.info("✅ Обработчик ошибок зарегистрирован")
        
        # Запускаем бота
        logger.info("🤖 Запуск бота...")
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True  # Сбрасываем старые обновления при запуске
        )
        
    except KeyboardInterrupt:
        logger.info("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

