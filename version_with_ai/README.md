# Версия с ИИ (резервная копия для восстановления)

Здесь сохранён код, чтобы снова включить **обсуждение результатов с ИИ** и **проверку Claude API при старте**, когда будете готовы.

Текущая ветка (для Railway/GitHub) — без ИИ: после анализа показывается сообщение «Ждите обновлений…» и контакт @climb_ai.

---

## Как восстановить ИИ

### 1. `app/main.py` — проверка Claude при запуске

В `post_init` после инициализации БД добавьте:

```python
# Тест Claude API при запуске
async def test_claude_on_startup():
    try:
        import anthropic
        from app.config import ANTHROPIC_API_KEY
        logger.info("🔍 ТЕСТИРУЕМ CLAUDE API ПРИ ЗАПУСКЕ...")
        if not ANTHROPIC_API_KEY:
            logger.error("❌ ANTHROPIC_API_KEY НЕ НАЙДЕН!")
            return False
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Скажи 'API работает!'"}]
        )
        logger.info("✅ Claude API готов к работе!")
        return True
    except Exception as e:
        logger.error(f"❌ ОШИБКА CLAUDE API: {e}")
        return False

claude_works = await test_claude_on_startup()
if not claude_works:
    logger.warning("⚠️ Claude API не работает - будет использоваться fallback")
```

### 2. `app/bot/handlers.py` — кнопка «Обсудить с ИИ»

**После отправки дашборда (два места):** вместо отправки `ANALYSIS_COMPLETE_MESSAGE` без кнопки — отправлять сообщение с кнопкой:

```python
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

context.user_data['analysis_result'] = result
keyboard = [[InlineKeyboardButton("🤖 Обсудить результаты с ИИ", callback_data="action_discuss_with_ai")]]
await context.bot.send_message(
    chat_id=...,  # update.message.chat_id или query.message.chat_id
    text="📊 Анализ завершен!\n\nХотите обсудить результаты с ИИ?",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
```

**В `handle_next_actions`:** раскомментировать:

```python
if action == "discuss_with_ai":
    await handle_discuss_with_ai(update, context)
    return
```

И добавить функцию `handle_discuss_with_ai` из файла `RESTORE_handle_discuss_with_ai.py` в этой папке.

### 3. Регистрация обработчика

Убедитесь, что в `setup_handlers` есть:

```python
application.add_handler(CallbackQueryHandler(handle_next_actions, pattern="^action_"))
```

и что `handle_discuss_with_ai` вызывается из `handle_next_actions` при `action == "discuss_with_ai"`.

Полный код функции `handle_discuss_with_ai` — в `RESTORE_handle_discuss_with_ai.py`.
