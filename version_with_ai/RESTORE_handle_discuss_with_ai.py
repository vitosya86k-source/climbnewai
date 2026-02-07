# Вставьте эту функцию в app/bot/handlers.py (вместо закомментированного блока).
# Удалите комментарий "# Обсуждение результатов с ИИ в этой версии отключено" и вставьте код ниже.

async def handle_discuss_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обсуждения результатов с ИИ"""
    query = update.callback_query

    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback: {e}")

    analysis_result = context.user_data.get('analysis_result')

    if not analysis_result:
        await query.edit_message_text(
            "❌ Ошибка: Нет данных анализа\n\n"
            "Пожалуйста, сначала обработайте видео."
        )
        return

    await query.edit_message_text("🤖 Отправляю метрики ИИ для обсуждения...")

    try:
        technique_metrics = analysis_result.get('technique_metrics', {})
        additional_metrics = analysis_result.get('additional_metrics', {})
        swot_analysis = analysis_result.get('swot_analysis', {})
        estimated_grade = analysis_result.get('estimated_grade', 'N/A')

        prompt_parts = [
            "📊 Анализ техники скалолазания:\n\n",
            "🎯 Метрики техники (7 базовых):\n"
        ]
        metric_names = {
            'quiet_feet': 'Quiet Feet (Точность ног)',
            'hip_position': 'Hip Position (Положение таза)',
            'diagonal': 'Противовес (Diagonal Movement)',
            'route_reading': 'Считывание (Route Reading)',
            'rhythm': 'Ритм (Movement Rhythm)',
            'dynamic_control': 'Контроль динамики (Dynamic Control)',
            'grip_release': 'Grip Release (Мягкость перехватов)'
        }
        for key, name in metric_names.items():
            value = technique_metrics.get(key, 50.0)
            prompt_parts.append(f"- {name}: {value:.1f}%\n")

        prompt_parts.append("\n📈 Дополнительные метрики:\n")
        additional_names = {
            'stability': 'Стабильность',
            'exhaustion': 'Истощение',
            'arm_efficiency': 'Эффективность рук',
            'leg_efficiency': 'Эффективность ног',
            'recovery': 'Восстановление'
        }
        for key, name in additional_names.items():
            value = additional_metrics.get(key, 50.0)
            prompt_parts.append(f"- {name}: {value:.1f}%\n")

        prompt_parts.append(f"\n🎯 Оценка уровня: {estimated_grade}\n")

        if swot_analysis:
            prompt_parts.append("\n💪 SWOT-анализ:\n")
            if swot_analysis.get('strengths'):
                prompt_parts.append("Сильные стороны:\n")
                for item in swot_analysis['strengths'][:3]:
                    prompt_parts.append(f"- {item.get('text', '')}\n")
            if swot_analysis.get('weaknesses'):
                prompt_parts.append("\nСлабые стороны:\n")
                for item in swot_analysis['weaknesses'][:3]:
                    prompt_parts.append(f"- {item.get('text', '')}\n")
            if swot_analysis.get('opportunities'):
                prompt_parts.append("\nВозможности:\n")
                for item in swot_analysis['opportunities'][:2]:
                    prompt_parts.append(f"- {item.get('text', '')}\n")
            if swot_analysis.get('threats'):
                prompt_parts.append("\nРиски:\n")
                for item in swot_analysis['threats'][:2]:
                    prompt_parts.append(f"- {item.get('text', '')}\n")

        prompt_text = "".join(prompt_parts)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📊 Метрики анализа:\n\n{prompt_text}"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🤖 Промпт для ИИ:\n\n```\n{prompt_text}\n```\n\n💬 Теперь вы можете обсудить эти результаты с ИИ.",
            parse_mode='Markdown'
        )
        logger.info("Метрики и промпт отправлены пользователю для обсуждения с ИИ")

    except Exception as e:
        logger.error(f"Ошибка при подготовке данных для ИИ: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Ошибка: {str(e)}\n\nПопробуйте еще раз."
        )
