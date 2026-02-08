"""Генератор отчетов (алгоритмический, без ИИ)"""

import logging
from typing import Dict, Any

from app.experts import select_expert
from app.psychology import determine_neuro_type
from app.boldering import find_similar_athletes, format_comparison

# 📊 Алгоритмический анализатор (без AI)
from app.analysis.algorithmic import generate_algorithmic_report

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Генерирует отчеты алгоритмически (без ИИ)"""
    
    def __init__(self):
        pass
    
    async def generate_report(
        self,
        analysis_data: Dict[str, Any],
        report_format: str,
        climber_name: str = "Скалолаз"
    ) -> Dict[str, Any]:
        """
        Генерирует полный отчет
        
        Returns:
            dict с ключами:
            - report_text: текст отчета
            - expert_assigned: имя эксперта
            - expert_score: оценка эксперта
            - neuro_type: нейротип
        """
        try:
            logger.info(f"🚀 Начинаем генерацию отчета в формате: {report_format}")
            logger.info(f"📊 Данные анализа: {list(analysis_data.keys()) if analysis_data else 'НЕТ ДАННЫХ'}")
            logger.info(f"👤 Имя скалолаза: {climber_name}")
            
            # 1. Выбираем эксперта
            expert_profile = select_expert(analysis_data)
            logger.info(f"Выбран эксперт: {expert_profile['name']}")
            
            # 2. Определяем нейротип
            neuro_profile = determine_neuro_type(analysis_data)
            logger.info(f"Определен нейротип: {neuro_profile['name']}")
            
            # 3. Находим похожих спортсменов
            similar_athletes = find_similar_athletes(analysis_data, top_n=3)
            logger.info(f"Найдено {len(similar_athletes)} похожих спортсменов")
            
            # 4. Генерируем отчет локально (без ИИ)
            report_text = self._generate_local_report(
                analysis_data, report_format, climber_name,
                expert_profile, neuro_profile, similar_athletes
            )
            
            logger.info(f"Отчет успешно сгенерирован ({len(report_text)} символов)")
            
            # Убираем markdown разметку
            report_text = self._remove_markdown(report_text)
            
            # 6. Добавляем падение если было
            if analysis_data.get('fall_detected') and analysis_data.get('fall_analysis'):
                from app.analysis.fall_detector import FallDetector
                fall_detector = FallDetector()
                fall_detector.fall_detected = True
                fall_detector.fall_frame = analysis_data['fall_frame']
                fall_detector.fall_timestamp = analysis_data['fall_timestamp']
                fall_detector.predictors = analysis_data.get('fall_predictors', [])
                
                fall_report = fall_detector.format_fall_report()
                report_text += "\n\n" + fall_report
            
            # 7. Добавляем сравнение с атлетами
            if similar_athletes and "СРАВНЕНИЕ С БАЗОЙ" not in report_text:
                comparison_text = format_comparison(similar_athletes, analysis_data['avg_pose_quality'])
                report_text += "\n\n" + comparison_text
            
            return {
                'report_text': report_text,
                'expert_assigned': expert_profile['name'],
                'expert_score': expert_profile['score'],
                'neuro_type': neuro_profile['name']
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            raise
    
    def _generate_local_report(
        self,
        analysis_data: Dict[str, Any],
        report_format: str,
        climber_name: str,
        expert_profile: dict,
        neuro_profile: dict,
        similar_athletes: list
    ) -> str:
        """Генерирует отчет локально без Claude API, используя AlgorithmicAnalyzer"""

        # 📊 Используем алгоритмический анализатор для основной части
        algorithmic_report = generate_algorithmic_report(analysis_data)

        quality = analysis_data.get('avg_pose_quality', 0)
        intensity = analysis_data.get('avg_motion_intensity', 0)
        balance = analysis_data.get('avg_balance_score', 0)
        overall = analysis_data.get('overall_quality', 0)
        frames = analysis_data.get('total_frames', 0)
        
        # Прогресс бары
        def progress_bar(value):
            filled = int(value / 10)
            return '█' * filled + '░' * (10 - filled)
        
        report = f"""
🎯 CLIMBAI АНАЛИЗ ДВИЖЕНИЯ

Привет, {climber_name}! 👋

📊 ОСНОВНАЯ СТАТИСТИКА
━━━━━━━━━━━━━━━━━━━━━━
• Кадров проанализировано: {frames}
• Продолжительность: {analysis_data.get('duration', 0):.1f}с
• Средний FPS: {analysis_data.get('fps', 30)}

⚡ МАТРИЦА ПРОИЗВОДИТЕЛЬНОСТИ
━━━━━━━━━━━━━━━━━━━━━━
КАЧЕСТВО ПОЗЫ:    {progress_bar(quality)} {quality:.1f}%
ИНТЕНСИВНОСТЬ:    {progress_bar(intensity)} {intensity:.1f}
БАЛАНС:           {progress_bar(balance)} {balance:.1f}%
ОБЩАЯ ОЦЕНКА:     {progress_bar(overall)} {overall:.1f}%

👨‍🏫 ЭКСПЕРТНЫЙ АНАЛИЗ
━━━━━━━━━━━━━━━━━━━━━━
Назначенный эксперт: {expert_profile['name']}
Оценка эксперта: {expert_profile['score']:.1f}/100

{self._get_expert_comment(quality, expert_profile['name'])}

🔬 БИОМЕХАНИЧЕСКИЙ АНАЛИЗ
━━━━━━━━━━━━━━━━━━━━━━
Качество детекции: {quality:.1f}%
{self._get_quality_interpretation(quality)}

Интенсивность движений: {intensity:.1f}
{self._get_intensity_interpretation(intensity)}

Баланс тела: {balance:.1f}%
{self._get_balance_interpretation(balance)}

🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ
━━━━━━━━━━━━━━━━━━━━━━
Определенный нейротип: {neuro_profile['name']}
{neuro_profile.get('description', '')}

Характерные черты:
{self._format_traits(neuro_profile.get('traits', []))}

🏆 СРАВНЕНИЕ С БАЗОЙ СПОРТСМЕНОВ
━━━━━━━━━━━━━━━━━━━━━━
{self._format_athletes(similar_athletes)}

💪 АНАЛИЗ НАПРЯЖЕНИЯ
━━━━━━━━━━━━━━━━━━━━━━
{self._format_tension_analysis(analysis_data.get('tension_analysis', {}))}

🏥 ПРОГНОЗ ТРАВМ
━━━━━━━━━━━━━━━━━━━━━━
{self._format_injury_prediction(analysis_data.get('injury_prediction', {}))}

📊 9-BOX ОЦЕНКА СКАЛОЛАЗА
━━━━━━━━━━━━━━━━━━━━━━
{self._format_nine_box(analysis_data.get('nine_box', {}))}

🎯 КЛЮЧЕВЫЕ МОМЕНТЫ
━━━━━━━━━━━━━━━━━━━━━━
Лучший кадр: #{analysis_data.get('best_frame', {}).get('frame_number', 'N/A')}
Худший кадр: #{analysis_data.get('worst_frame', {}).get('frame_number', 'N/A')}

{'🚨 ОБНАРУЖЕНО ПАДЕНИЕ!' if analysis_data.get('fall_detected') else '✅ Падений не обнаружено'}

⚡ ПЛАН ДЕЙСТВИЙ
━━━━━━━━━━━━━━━━━━━━━━
🎯 ПРЯМО СЕГОДНЯ (5 минут):
{self._get_immediate_actions(quality, balance)}

📅 НА ЭТОЙ НЕДЕЛЕ:
{self._get_weekly_actions(quality, intensity)}

🚀 НА МЕСЯЦ:
{self._get_monthly_goal(overall)}

━━━━━━━━━━━━━━━━━━━━━━

{algorithmic_report}

━━━━━━━━━━━━━━━━━━━━━━
"""
        return report.strip()
    
    def _get_expert_comment(self, quality: float, expert: str) -> str:
        if quality >= 80:
            return f"Отличная техника! {expert} был бы впечатлен твоей стабильностью."
        elif quality >= 60:
            return f"Хорошая база, но есть над чем работать. {expert} рекомендует больше практики."
        else:
            return f"Техника требует серьезной работы. {expert} советует начать с основ."
    
    def _get_quality_interpretation(self, quality: float) -> str:
        if quality >= 80:
            return "Превосходно! Тело отлично детектируется, поза стабильная."
        elif quality >= 60:
            return "Хорошо. Большинство кадров четкие, есть моменты нестабильности."
        else:
            return "Требуется улучшение. Много кадров с плохой видимостью ключевых точек."
    
    def _get_intensity_interpretation(self, intensity: float) -> str:
        if intensity >= 2.0:
            return "Очень динамичные движения! Высокая активность."
        elif intensity >= 1.0:
            return "Умеренная интенсивность. Сбалансированный темп."
        else:
            return "Низкая интенсивность. Статичные позы или медленные движения."
    
    def _get_balance_interpretation(self, balance: float) -> str:
        if balance >= 80:
            return "Отличный баланс! Центр масс стабилен."
        elif balance >= 60:
            return "Неплохой баланс, но есть моменты нестабильности."
        else:
            return "Баланс требует работы. Центр масс часто смещается."
    
    def _format_traits(self, traits: list) -> str:
        return '\n'.join([f"• {trait}" for trait in traits[:3]])
    
    def _format_athletes(self, athletes: list) -> str:
        if not athletes:
            return "• Данные пока собираются"
        
        result = []
        for item in athletes[:3]:
            athlete = item['athlete_data']
            sim = item['similarity']
            result.append(f"• {athlete['name']}: {sim:.0f}% сходства - {athlete.get('description', '')}")
        return '\n'.join(result)
    
    def _get_immediate_actions(self, quality: float, balance: float) -> str:
        actions = []
        if quality < 70:
            actions.append("1. Улучши освещение при съемке")
            actions.append("2. Снимай с более выгодного угла")
        else:
            actions.append("1. Сделай разминку 3 минуты")
            actions.append("2. Повтори одно движение 5 раз")
        
        if balance < 70:
            actions.append("3. Постой на одной ноге 30 сек")
        else:
            actions.append("3. Запиши свои ощущения")
        
        return '\n'.join(actions)
    
    def _get_weekly_actions(self, quality: float, intensity: float) -> str:
        actions = ["• Анализируй по 2-3 видео в неделю"]
        
        if quality < 70:
            actions.append("• Работай над стабильностью движений")
        if intensity < 1.5:
            actions.append("• Добавь динамических упражнений")
        
        return '\n'.join(actions)
    
    def _get_monthly_goal(self, overall: float) -> str:
        target = overall + 10
        return f"• Достичь общей оценки {target:.0f}% (сейчас {overall:.1f}%)"
    
    def generate_simple_report(self, analysis_data: Dict[str, Any]) -> str:
        """
        Генерирует простой отчет без Claude API (для тестирования)
        """
        report = f"""
📊 БЫСТРЫЙ АНАЛИЗ
===================

СТАТИСТИКА:
• Кадров: {analysis_data.get('total_frames', 0)}
• Среднее качество: {analysis_data.get('avg_pose_quality', 0):.1f}%
• Интенсивность: {analysis_data.get('avg_motion_intensity', 0):.1f}
• Баланс: {analysis_data.get('avg_balance_score', 0):.1f}%
• Общее качество: {analysis_data.get('overall_quality', 0):.1f}%

ОЦЕНКА:
{self._get_quality_assessment(analysis_data.get('avg_pose_quality', 0))}

РЕКОМЕНДАЦИИ:
• Работай над стабильностью позы
• Следи за балансом
• Анализируй свои движения
"""
        return report.strip()
    
    def _get_quality_assessment(self, quality: float) -> str:
        """Простая оценка качества"""
        if quality >= 90:
            return "⭐⭐⭐⭐⭐ Отлично! Профессиональный уровень."
        elif quality >= 80:
            return "⭐⭐⭐⭐ Хорошо! Продвинутый уровень."
        elif quality >= 70:
            return "⭐⭐⭐ Удовлетворительно. Есть над чем работать."
        elif quality >= 60:
            return "⭐⭐ Посредственно. Требуется улучшение техники."
        else:
            return "⭐ Много работы впереди. Фокусируйся на базовых навыках."

    def _format_tension_analysis(self, tension_data: Dict[str, Any]) -> str:
        """Форматирует анализ напряжения"""
        if not tension_data:
            return "• Данные недоступны"

        tension_index = tension_data.get('overall_tension_index', 0)
        risk_level = tension_data.get('risk_level', 'LOW')
        zones = tension_data.get('zones', {})

        # Индекс напряжения
        result = [f"Общий индекс напряжения: {tension_index:.1f}/100"]

        # Уровень риска с эмодзи
        risk_emoji = {
            'LOW': '✅',
            'MODERATE': '🟡',
            'HIGH': '⚠️',
            'CRITICAL': '🔴'
        }
        result.append(f"Уровень риска: {risk_emoji.get(risk_level, '❓')} {risk_level}")

        # Проблемные зоны
        if zones:
            problem_zones = [
                name for name, data in zones.items()
                if data.get('classification') in ['HIGH', 'MODERATE']
            ]
            if problem_zones:
                result.append(f"\nПроблемные зоны: {', '.join(problem_zones)}")

        # Рекомендации
        recommendations = tension_data.get('recommendations', [])
        if recommendations:
            result.append("\nРекомендации:")
            for rec in recommendations[:3]:
                result.append(f"• {rec}")

        return '\n'.join(result)

    def _format_injury_prediction(self, injury_data: Dict[str, Any]) -> str:
        """Форматирует прогноз травм"""
        if not injury_data:
            return "• Риски не выявлены"

        predictions = injury_data.get('predictions', {})
        if not predictions:
            return "• Риски не выявлены ✅"

        # Фильтруем значимые риски
        significant_risks = {
            injury_type: pred
            for injury_type, pred in predictions.items()
            if pred.get('risk_level') in ['MODERATE', 'HIGH', 'CRITICAL']
        }

        if not significant_risks:
            return "• Все показатели в норме ✅"

        result = []
        risk_emoji = {
            'MODERATE': '🟡',
            'HIGH': '⚠️',
            'CRITICAL': '🔴'
        }

        for injury_type, pred in list(significant_risks.items())[:3]:  # Топ-3
            risk_level = pred.get('risk_level', 'LOW')
            probability = pred.get('probability', 0)
            timeline = pred.get('timeline', 'неизвестно')
            areas = pred.get('body_part', 'неизвестно')

            result.append(
                f"{risk_emoji.get(risk_level, '❓')} {injury_type.replace('_', ' ').title()}\n"
                f"  Вероятность: {probability * 100:.0f}% | Прогноз: {timeline}\n"
                f"  Зоны риска: {areas}"
            )

            # Добавляем одну меру профилактики
            prevention = pred.get('prevention_measures', [])
            if prevention:
                result.append(f"  💡 {prevention[0]}")

        return '\n\n'.join(result)

    def _format_nine_box(self, nine_box_data: Dict[str, Any]) -> str:
        """Форматирует 9-box оценку"""
        if not nine_box_data:
            return "• Данные недоступны"

        skill = nine_box_data.get('skill_score', 0)
        physical = nine_box_data.get('physical_score', 0)
        mental = nine_box_data.get('mental_score', 0)
        category = nine_box_data.get('category', 'UNKNOWN')
        description = nine_box_data.get('description', '')

        # Форматируем оценки
        def format_score(score):
            bars = int(score)
            return '█' * bars + '░' * (10 - bars)

        label = nine_box_data.get('label', '')

        result = [
            f"{label}",
            f"{description}",
            "",
            f"Технические навыки:  {format_score(skill)} {skill:.1f}/10",
            f"Физические данные:   {format_score(physical)} {physical:.1f}/10",
            f"Психологическое:     {format_score(mental)} {mental:.1f}/10",
        ]

        # Рекомендации
        recommendations = nine_box_data.get('recommendations', [])
        if recommendations:
            result.append("\nРекомендации:")
            for rec in recommendations[:3]:
                result.append(f"• {rec}")

        # Позиция в матрице (опционально)
        position = nine_box_data.get('position', {})
        if position:
            result.append(f"\nПозиция: {position.get('skill', '')}/{position.get('physical', '')}/{position.get('mental', '')}")

        return '\n'.join(result)

    def _remove_markdown(self, text: str) -> str:
        """Убирает markdown разметку из текста"""
        import re
        
        # Убираем ** (жирный текст)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        
        # Убираем # заголовки (но сохраняем текст)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Убираем --- разделители
        text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^═══+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^━━━+\s*$', '', text, flags=re.MULTILINE)
        
        # Убираем * (курсив)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Убираем лишние пустые строки (больше 2 подряд)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
