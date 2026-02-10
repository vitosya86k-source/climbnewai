"""
Генератор дашборда с метриками ClimbAI

Создает визуальный дашборд с основными метриками анализа видео скалолазания.
Может экспортировать в PNG или PDF.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
import math
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime

logger = logging.getLogger(__name__)

# Цвета согласно dashboard_prototype.html (в формате для matplotlib)
DASHBOARD_COLORS = {
    # Фон
    "background": "#1a1a2e",
    "card_bg": (1.0, 1.0, 1.0, 0.03),  # RGBA кортеж
    
    # Текст
    "text_primary": "#e8e8e8",
    "text_secondary": "#888888",
    "text_muted": "#666666",
    
    # Акценты
    "accent_blue": "#00d4ff",
    "accent_green": "#00ff88",
    "gradient_start": "#00d4ff",
    "gradient_end": "#00ff88",
    
    # Уровни метрик
    "excellent": "#00ff88",  # >= 75%
    "good": "#88ff00",       # 60-74%
    "medium": "#ffcc00",     # 45-59%
    "poor": "#ff6b6b",       # < 45%
    
    # SWOT карточки (RGBA кортежи для matplotlib)
    "strengths_border": (0, 1.0, 0.53, 0.5),      # зелёный
    "strengths_bg": (0, 1.0, 0.53, 0.1),
    "weaknesses_border": (1.0, 0.8, 0, 0.5),      # жёлтый
    "weaknesses_bg": (1.0, 0.8, 0, 0.1),
    "opportunities_border": (0, 0.83, 1.0, 0.5),  # голубой
    "opportunities_bg": (0, 0.83, 1.0, 0.1),
    "threats_border": (1.0, 0.42, 0.42, 0.5),     # красный
    "threats_bg": (1.0, 0.42, 0.42, 0.1),
}


class DashboardGenerator:
    """Генератор дашборда с метриками"""
    
    def __init__(self, width: int = 1920, height: int = 1080):
        """
        Args:
            width: ширина дашборда в пикселях
            height: высота дашборда в пикселях
        """
        self.width = width
        self.height = height
        self.bg_color = (20, 20, 30)  # Темный фон
        self.text_color = (255, 255, 255)  # Белый текст
        self.accent_color = (100, 150, 255)  # Синий акцент
        
    def generate_dashboard(
        self,
        analysis_data: Dict[str, Any],
        output_path: Path,
        format: str = "png"
    ) -> Path:
        """
        Генерирует дашборд с метриками
        
        Args:
            analysis_data: данные анализа видео
            output_path: путь для сохранения
            format: формат вывода ('png' или 'pdf')
            
        Returns:
            Path к сохраненному файлу
        """
        try:
            if format.lower() == "pdf":
                return self._generate_pdf_dashboard(analysis_data, output_path)
            else:
                return self._generate_png_dashboard(analysis_data, output_path)
        except Exception as e:
            logger.error(f"Ошибка генерации дашборда: {e}", exc_info=True)
            raise
    
    def _generate_png_dashboard(
        self,
        analysis_data: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """Генерирует PNG дашборд используя matplotlib"""
        fig = plt.figure(figsize=(12, 16), facecolor=DASHBOARD_COLORS['background'])
        
        # === HEADER ===
        self._draw_header(fig, analysis_data)
        
        # === TECHNIQUE SECTION (паутинка + список метрик) ===
        technique_metrics = analysis_data.get('technique_metrics', {})
        # Вычисляем общий балл (сначала берём готовый из анализа, если есть)
        overall_score = analysis_data.get('overall_technique_score')
        if overall_score is None:
            if technique_metrics:
                base_metrics = ['quiet_feet', 'hip_position', 'diagonal', 'route_reading', 
                               'rhythm', 'dynamic_control', 'grip_release']
                valid_values = []
                for key in base_metrics:
                    val = technique_metrics.get(key)
                    if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
                        valid_values.append(float(val))
                overall_score = sum(valid_values) / len(valid_values) if valid_values else 0
            else:
                overall_score = 0
        
        # Уровень берем из анализа или вычисляем заново
        grade = analysis_data.get('estimated_grade', 'N/A')
        grade_score = analysis_data.get('grade_score')
        if grade == 'N/A' and technique_metrics:
            # Вычисляем уровень на основе взвешенной суммы
            from app.analysis.swot_generator import SWOTGenerator
            swot_gen = SWOTGenerator()
            grade = swot_gen.estimate_grade(technique_metrics)
            grade_score = None
        
        self._create_technique_section(fig, technique_metrics, overall_score, grade, grade_score)
        
        # === SWOT GRID ===
        swot = analysis_data.get('swot_analysis', {})
        self._draw_swot_grid(fig, swot)
        
        # === ADDITIONAL METRICS ===
        additional = analysis_data.get('additional_metrics', {})
        self._draw_additional_metrics_section(fig, additional)
        
        # === FOOTER ===
        self._draw_footer(fig)
        
        # Сохраняем
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, facecolor=DASHBOARD_COLORS['background'], 
                   bbox_inches='tight', pad_inches=0.2)
        plt.close()
        
        
        logger.info(f"Дашборд сохранен: {output_path}")
        return output_path
    
    def _draw_header(self, fig, analysis_data: Dict[str, Any]):
        """Отрисовка header с логотипом и метаданными"""
        from datetime import datetime
        
        # Логотип и название (без эмодзи для совместимости)
        fig.text(0.05, 0.98, 'ClimbAI', fontsize=28, fontweight='bold', 
                color=DASHBOARD_COLORS['accent_blue'], ha='left', va='top', transform=fig.transFigure)
        # Подзаголовок "BoulderVision Analysis" убран — дата и время только в футере
    
    def _draw_metrics_list(self, ax, technique_metrics: Dict[str, float], overall_score: float, grade: str, grade_score: float | None = None):
        """Отрисовка списка метрик с прогресс-барами"""
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')
        ax.set_facecolor(DASHBOARD_COLORS['background'])
        
        # Названия метрик: (ключ, аббревиатура, русское название)
        metrics_info = [
            ("quiet_feet", "QF", "Спокойные ноги"),
            ("hip_position", "HP", "Положение таза"),
            ("diagonal", "DM", "Диагональная координация"),
            ("route_reading", "RR", "Считывание маршрута"),
            ("rhythm", "RT", "Ритм"),
            ("dynamic_control", "DC", "Контроль динамики"),
            ("grip_release", "GR", "Плавность перехватов"),
        ]
        
        y_start = 95
        y_step = 12  # Компактнее (было 16)
        bar_height = 4
        bar_width = 43
        x_label = 2
        x_bar = 52
        
        for i, (key, name, hint) in enumerate(metrics_info):
            y = y_start - i * y_step
            
            # Получаем значение метрики
            score = technique_metrics.get(key, 50)
            if score is None or (isinstance(score, float) and math.isnan(score)):
                score = 50
            score = max(0.0, min(100.0, float(score)))
            
            # Определяем цвет
            if score >= 75:
                color = DASHBOARD_COLORS['excellent']
            elif score >= 60:
                color = DASHBOARD_COLORS['good']
            elif score >= 45:
                color = DASHBOARD_COLORS['medium']
            else:
                color = DASHBOARD_COLORS['poor']
            
            # Название метрики (адаптивный размер для длинных строк)
            label_fontsize = 12 if len(name) <= 18 else 10
            ax.text(x_label, y + 2, name, fontsize=label_fontsize, fontweight='bold',
                    color=DASHBOARD_COLORS['text_primary'], va='center')
            
            # Короткие описания (без длинных текстов)
            short_descriptions = {
                "QF": "Точность постановки ног",
                "HP": "Положение таза у стены",
                "DM": "Диагональная координация",
                "RR": "Планирование маршрута",
                "RT": "Равномерность темпа",
                "DC": "Контроль после бросков",
                "GR": "Плавность перехватов",
            }
            
            # Короткое описание (одна строка, увеличен размер)
            desc = short_descriptions.get(name, hint)
            desc_fontsize = 11 if len(desc) <= 28 else 10
            ax.text(
                x_label,
                y - 2,
                desc,
                fontsize=desc_fontsize,
                color=DASHBOARD_COLORS['text_secondary'],
                va='center',
                wrap=True,
            )
            
            # Фон прогресс-бара
            bar_bg = mpatches.Rectangle((x_bar, y - bar_height/2), bar_width, bar_height,
                                        facecolor='#333333', edgecolor='none')
            ax.add_patch(bar_bg)
            
            # Заполнение прогресс-бара
            fill_width = bar_width * (score / 100)
            bar_fill = mpatches.Rectangle((x_bar, y - bar_height/2), fill_width, bar_height,
                                          facecolor=color, edgecolor='none')
            ax.add_patch(bar_fill)
            
            # Значение справа от бара (не поверх заливки)
            value_text = f"{int(score)}%"
            value_x = min(98, x_bar + bar_width + 2)
            ax.text(value_x, y, value_text, fontsize=12, fontweight='bold',
                    color=color, va='center', ha='left')

        # Общий балл и уровень — после GR, в этой же колонке
        summary_y = y_start - (len(metrics_info) - 1) * y_step - 14
        ax.text(x_label, summary_y, f"Общий балл: {int(overall_score)}/100",
                fontsize=12, fontweight='bold', color=DASHBOARD_COLORS['text_primary'], va='center')
        level_text = f"Уровень: {grade}"
        if isinstance(grade_score, (int, float)):
            level_text = f"Уровень: {grade} (score: {grade_score:.1f})"
        ax.text(x_label, summary_y - 8, level_text,
                fontsize=11, color=DASHBOARD_COLORS['accent_blue'], va='center')
    
    def _create_technique_section(self, fig, technique_metrics: Dict[str, float], 
                                  overall_score: float, grade: str, grade_score: float | None = None):
        """Создание секции техники с паутинкой И списком метрик"""
        # Создаём gridspec для двух колонок
        gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=0.1,
                              left=0.05, right=0.95, top=0.90, bottom=0.55,
                              figure=fig)
        
        # Левая колонка: список метрик
        ax_list = fig.add_subplot(gs[0, 0])
        self._draw_metrics_list(ax_list, technique_metrics, overall_score, grade, grade_score)
        
        # Правая колонка: паутинка
        ax_spider = fig.add_subplot(gs[0, 1], projection='polar')
        self._draw_spider_chart_polar(ax_spider, technique_metrics)
        
        # Подгоняем высоту паутинки под высоту списка (выравнивание по верху)
        list_pos = ax_list.get_position()
        spider_pos = ax_spider.get_position()
        ax_spider.set_position([spider_pos.x0, list_pos.y0, spider_pos.width, list_pos.height])

        # Общий балл и уровень переносятся в список метрик после GR
    
    def _draw_spider_chart_polar(self, ax, technique_metrics: Dict[str, float]):
        """Рисует паутинку метрик в полярных координатах"""
        ax.set_facecolor(DASHBOARD_COLORS['background'])
        
        # 7 метрик - порядок для паутинки по часовой стрелке: DM, HP, QF, GR, DC, RT, RR (начиная сверху)
        categories = ['DM', 'HP', 'QF', 'GR', 'DC', 'RT', 'RR']
        keys = ['diagonal', 'hip_position', 'quiet_feet', 'grip_release', 'dynamic_control', 'rhythm', 'route_reading']
        
        values = []
        for key in keys:
            val = technique_metrics.get(key, 50)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                val = 50.0
            values.append(max(0.0, min(100.0, float(val))))
        
        # Углы для осей - стандартный расчет (matplotlib по умолчанию)
        # Порядок метрик уже правильный: QF, HP, DM, RR, RT, DC, GR
        # Первая метрика (QF) будет в стандартной позиции
        angles = [n / len(categories) * 2 * math.pi for n in range(len(categories))]
        angles += angles[:1]  # Замыкаем круг
        values += values[:1]  # Замыкаем значения
        
        # Рисуем паутинку (размер как был)
        ax.plot(angles, values, 'o-', linewidth=2, color=DASHBOARD_COLORS['accent_blue'], label='Метрики')
        ax.fill(angles, values, alpha=0.3, color=DASHBOARD_COLORS['accent_blue'])
        
        # Концентрические круги
        for i in [25, 50, 75, 100]:
            ax.plot(angles, [i] * len(angles), '--', linewidth=0.5, 
                   color=DASHBOARD_COLORS['text_secondary'], alpha=0.3)
        
        # Подписи осей (увеличен размер шрифта)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=14, color=DASHBOARD_COLORS['text_primary'], fontweight='bold')
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(['25', '50', '75', '100'], fontsize=11, 
                          color=DASHBOARD_COLORS['text_secondary'])
        ax.grid(True, alpha=0.3, color=DASHBOARD_COLORS['text_secondary'])
        
        # Цифры внутри паутины убраны — мешают восприятию
    
    def _generate_pdf_dashboard(
        self,
        analysis_data: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """Генерирует PDF дашборд"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with PdfPages(output_path) as pdf:
            fig = plt.figure(figsize=(19.2, 10.8), facecolor='#14141e')
            fig.suptitle('ClimbAI - Анализ пролаза', 
                         fontsize=32, color='white', fontweight='bold', y=0.98)
            
            gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3, 
                                 left=0.05, right=0.95, top=0.93, bottom=0.05)
            
            ax1 = fig.add_subplot(gs[0:2, 0:2])
            self._draw_spider_chart(ax1, analysis_data)
            
            ax2 = fig.add_subplot(gs[0, 2:])
            self._draw_weight_distribution(ax2, analysis_data)
            
            ax3 = fig.add_subplot(gs[1, 2:])
            self._draw_tension_zones(ax3, analysis_data)
            
            ax4 = fig.add_subplot(gs[2, 0:2])
            self._draw_speed_profile(ax4, analysis_data)
            
            ax5 = fig.add_subplot(gs[2, 2:])
            self._draw_summary_stats(ax5, analysis_data)
            
            pdf.savefig(fig, facecolor='#14141e', bbox_inches='tight', pad_inches=0.2)
            plt.close()
        
        logger.info(f"PDF дашборд сохранен: {output_path}")
        return output_path
    
    def _draw_spider_chart(self, ax, analysis_data: Dict[str, Any]):
        """Рисует паутинку метрик"""
        ax.set_facecolor('#14141e')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        
        # Получаем метрики (НОВАЯ КОНЦЕПЦИЯ: 7 базовых метрик техники)
        technique_metrics = analysis_data.get('technique_metrics', {})
        if not technique_metrics:
            # Fallback на старые метрики для обратной совместимости
            metrics = analysis_data.get('metrics', {})
            if not metrics:
                metrics = self._extract_metrics(analysis_data)
            technique_metrics = metrics
        
        # НОВАЯ КОНЦЕПЦИЯ: 7 метрик
        categories = ['Quiet Feet', 'Hip Position', 'Противовес', 'Считывание', 'Ритм', 'Динамика', 'Grip Release']
        keys = ['quiet_feet', 'hip_position', 'diagonal', 'route_reading', 'rhythm', 'dynamic_control', 'grip_release']
        
        # Если новых метрик нет, используем старые
        if not any(key in technique_metrics for key in keys):
            categories = ['Сила', 'Баланс', 'Координация', 'Техника']
            keys = ['сила', 'баланс', 'координация', 'техника']
        
        values = []
        for key in keys:
            val = technique_metrics.get(key, 50)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                val = 50.0
            values.append(max(0.0, min(100.0, float(val))))
        
        # Углы для осей
        angles = [n / len(categories) * 2 * math.pi for n in range(len(categories))]
        angles += angles[:1]  # Замыкаем круг
        values += values[:1]
        
        # Рисуем паутинку
        ax.plot(angles, values, 'o-', linewidth=2, color='#6496ff', label='Метрики')
        ax.fill(angles, values, alpha=0.25, color='#6496ff')
        
        # Концентрические круги
        for i in [25, 50, 75, 100]:
            ax.plot(angles, [i] * len(angles), '--', linewidth=0.5, color='gray', alpha=0.5)
        
        # Подписи осей
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=14, color='white')
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(['25', '50', '75', '100'], fontsize=10, color='white')
        ax.grid(True, alpha=0.3, color='gray')
        ax.set_title('Основные метрики', fontsize=16, color='white', fontweight='bold', pad=20)
        
        # Значения на точках
        for angle, value, cat in zip(angles[:-1], values[:-1], categories):
            x = value * math.cos(angle)
            y = value * math.sin(angle)
            ax.text(x * 1.15, y * 1.15, f'{int(value)}', 
                   ha='center', va='center', fontsize=12, color='white', fontweight='bold')
    
    def _draw_weight_distribution(self, ax, analysis_data: Dict[str, Any]):
        """Рисует распределение нагрузки"""
        ax.set_facecolor('#14141e')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        
        # Получаем данные о нагрузке
        weight_data = analysis_data.get('weight_distribution', {})
        if not weight_data:
            weight_data = {
                'left_arm': 25.0,
                'right_arm': 25.0,
                'left_leg': 25.0,
                'right_leg': 25.0
            }
        
        limbs = ['Левая рука', 'Правая рука', 'Левая нога', 'Правая нога']
        values = [
            weight_data.get('left_arm', 25.0),
            weight_data.get('right_arm', 25.0),
            weight_data.get('left_leg', 25.0),
            weight_data.get('right_leg', 25.0)
        ]
        
        # Валидация
        values = [max(0.0, min(100.0, float(v) if v is not None else 25.0)) for v in values]
        
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#F44336']
        bars = ax.bar(limbs, values, color=colors, alpha=0.8, edgecolor='white', linewidth=2)
        
        # Подписи значений
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.1f}%',
                   ha='center', va='bottom', fontsize=12, color='white', fontweight='bold')
        
        ax.set_ylabel('Нагрузка (%)', fontsize=12, color='white')
        ax.set_title('Распределение нагрузки', fontsize=14, color='white', fontweight='bold')
        ax.set_ylim(0, max(100, max(values) * 1.2))
        ax.grid(True, alpha=0.3, color='gray', axis='y')
    
    def _draw_tension_zones(self, ax, analysis_data: Dict[str, Any]):
        """Рисует зоны напряжения"""
        ax.set_facecolor('#14141e')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        
        # Получаем данные о напряжении
        tension_data = analysis_data.get('tension_analysis', {}).get('zones', {})
        if not tension_data:
            tension_data = {
                'левое_плечо': 0,
                'правое_плечо': 0,
                'левый_локоть': 0,
                'правый_локоть': 0,
                'поясница': 0
            }
        
        zones = list(tension_data.keys())
        values = [max(0.0, min(100.0, float(v) if v is not None else 0.0)) 
                 for v in tension_data.values()]
        
        # Цвета по уровню напряжения
        colors = []
        for v in values:
            if v < 20:
                colors.append('#4CAF50')  # Зеленый
            elif v < 50:
                colors.append('#FFC107')  # Желтый
            elif v < 75:
                colors.append('#FF9800')  # Оранжевый
            else:
                colors.append('#F44336')  # Красный
        
        bars = ax.barh(zones, values, color=colors, alpha=0.8, edgecolor='white', linewidth=1)
        
        # Подписи
        for bar, val in zip(bars, values):
            width = bar.get_width()
            ax.text(width + 2, bar.get_y() + bar.get_height()/2.,
                   f'{val:.1f}',
                   ha='left', va='center', fontsize=10, color='white', fontweight='bold')
        
        ax.set_xlabel('Уровень напряжения', fontsize=12, color='white')
        ax.set_title('Зажимы и риски', fontsize=14, color='white', fontweight='bold')
        ax.set_xlim(0, 100)
        ax.grid(True, alpha=0.3, color='gray', axis='x')
    
    def _draw_speed_profile(self, ax, analysis_data: Dict[str, Any]):
        """Рисует профиль скорости"""
        ax.set_facecolor('#14141e')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        
        # Получаем данные о скорости
        bv_data = analysis_data.get('bouldervision', {})
        velocity_data = bv_data.get('velocity_history', [])
        
        if not velocity_data:
            # Создаем примерные данные
            velocity_data = [0.01 + 0.02 * np.sin(i/10) for i in range(100)]
        
        # Ограничиваем до разумного размера
        velocity_data = velocity_data[:200]
        
        time_points = np.arange(len(velocity_data))
        ax.plot(time_points, velocity_data, color='#6496ff', linewidth=2, label='Скорость')
        ax.fill_between(time_points, velocity_data, alpha=0.3, color='#6496ff')
        
        ax.set_xlabel('Кадр', fontsize=12, color='white')
        ax.set_ylabel('Скорость', fontsize=12, color='white')
        ax.set_title('Профиль скорости движения', fontsize=14, color='white', fontweight='bold')
        ax.grid(True, alpha=0.3, color='gray')
        ax.legend(loc='upper right', facecolor='#14141e', edgecolor='white', labelcolor='white')
    
    def _draw_swot_grid(self, fig, swot: Dict[str, Any]):
        """Рисует SWOT Grid (4 карточки)"""
        if not swot:
            return
        
        # Создаём gridspec для 2x2 сетки
        gs = fig.add_gridspec(2, 2, hspace=0.15, wspace=0.1,
                              left=0.05, right=0.95, top=0.52, bottom=0.22,
                              figure=fig)
        
        # Strengths (верхний левый)
        ax_s = fig.add_subplot(gs[0, 0])
        self._draw_swot_card(ax_s, 'strengths', swot.get('strengths', [])[:4], 
                           DASHBOARD_COLORS['strengths_bg'], 
                           DASHBOARD_COLORS['strengths_border'],
                           DASHBOARD_COLORS['excellent'])
        
        # Weaknesses (верхний правый)
        ax_w = fig.add_subplot(gs[0, 1])
        self._draw_swot_card(ax_w, 'weaknesses', swot.get('weaknesses', [])[:4],
                           DASHBOARD_COLORS['weaknesses_bg'],
                           DASHBOARD_COLORS['weaknesses_border'],
                           DASHBOARD_COLORS['medium'])
        
        # Opportunities (нижний левый)
        ax_o = fig.add_subplot(gs[1, 0])
        self._draw_swot_card(ax_o, 'opportunities', swot.get('opportunities', [])[:3],
                           DASHBOARD_COLORS['opportunities_bg'],
                           DASHBOARD_COLORS['opportunities_border'],
                           DASHBOARD_COLORS['accent_blue'])
        
        # Threats (нижний правый)
        ax_t = fig.add_subplot(gs[1, 1])
        self._draw_swot_card(ax_t, 'threats', swot.get('threats', [])[:3],
                           DASHBOARD_COLORS['threats_bg'],
                           DASHBOARD_COLORS['threats_border'],
                           DASHBOARD_COLORS['poor'])
    
    def _draw_swot_card(self, ax, card_type: str, items: List[Dict], 
                        bg_color: str, border_color: str, text_color: str):
        """Отрисовка одной SWOT карточки"""
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')
        
        # Фон карточки
        card_bg = mpatches.Rectangle((2, 2), 96, 96, 
                                     facecolor=bg_color, 
                                     edgecolor=border_color, 
                                     linewidth=2)
        ax.add_patch(card_bg)
        
        # Заголовки на русском
        titles = {
            'strengths': 'СИЛЬНЫЕ СТОРОНЫ',
            'weaknesses': 'СЛАБЫЕ СТОРОНЫ',
            'opportunities': 'ЗОНЫ РОСТА',
            'threats': 'РИСКИ'
        }
        
        ax.text(50, 90, titles.get(card_type, card_type.upper()), 
               fontsize=12, fontweight='bold', color=text_color,
               ha='center', va='top')
        
        # Элементы списка (уменьшено для помещения больше текста)
        y_start = 75
        y_step = 20  # Увеличено расстояние между элементами для 3 строк
        
        for i, item in enumerate(items[:4]):
            base_y = y_start - i * y_step
            text = item.get('text', '')
            
            # Разбиваем текст на строки (максимум 3 строки по 44 символа)
            words = text.split()
            lines = []
            current_line = ''
            
            for word in words:
                test_line = current_line + (' ' + word if current_line else word)
                if len(test_line) <= 44:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    if len(lines) >= 3:  # Максимум 3 строки
                        # Если не поместилось, добавляем оставшиеся слова в последнюю строку с троеточием
                        remaining_words = words[words.index(word):]
                        remaining = ' '.join(remaining_words)
                        if len(remaining) > 44:
                            remaining = remaining[:41].rstrip() + "..."
                        lines.append(remaining)
                        break
            
            if current_line and len(lines) < 3:
                lines.append(current_line)
            
            # Рисуем строки (до 3 строк)
            for line_idx, line_text in enumerate(lines[:3]):
                y = base_y - line_idx * 7
                
                if line_idx == 0:
                    # Точка-маркер только для первой строки
                    circle = mpatches.Circle((8, y), 2.5, facecolor=text_color)
                    ax.add_patch(circle)
                
                ax.text(14, y, line_text, fontsize=10, 
                       color=DASHBOARD_COLORS['text_primary'],
                       va='center', ha='left')
            
            # УБРАНО: Процент справа (дублируется в тексте)
    
    def _draw_swot_analysis(self, ax, analysis_data: Dict[str, Any]):
        """Рисует SWOT-анализ (старая версия для обратной совместимости)"""
        swot = analysis_data.get('swot_analysis', {})
        if not swot:
            ax.text(0.5, 0.5, 'SWOT-анализ недоступен', 
                   ha='center', va='center', fontsize=14, 
                   color=DASHBOARD_COLORS['text_primary'], transform=ax.transAxes)
            return
        
        # Заголовок
        ax.text(0.5, 0.95, 'SWOT-анализ', fontsize=18, 
               color=DASHBOARD_COLORS['text_primary'], 
               fontweight='bold', ha='center', transform=ax.transAxes)
        
        y_start = 0.85
        y_step = 0.12
        
        # Strengths
        strengths = swot.get('strengths', [])[:3]
        if strengths:
            ax.text(0.05, y_start, '💪 Сильные стороны:', fontsize=12, 
                   color=DASHBOARD_COLORS['excellent'], 
                   fontweight='bold', transform=ax.transAxes)
            for i, item in enumerate(strengths):
                text = item.get('text', '')[:80] + '...' if len(item.get('text', '')) > 80 else item.get('text', '')
                ax.text(0.05, y_start - (i+1) * y_step, f"• {text}", fontsize=9, 
                       color=DASHBOARD_COLORS['text_primary'], transform=ax.transAxes)
        
        # Weaknesses
        weaknesses = swot.get('weaknesses', [])[:3]
        if weaknesses:
            y_weak = y_start - len(strengths) * y_step - 0.1 if strengths else y_start
            ax.text(0.05, y_weak, '⚠️ Слабые стороны:', fontsize=12, 
                   color=DASHBOARD_COLORS['medium'], 
                   fontweight='bold', transform=ax.transAxes)
            for i, item in enumerate(weaknesses):
                text = item.get('text', '')[:80] + '...' if len(item.get('text', '')) > 80 else item.get('text', '')
                ax.text(0.05, y_weak - (i+1) * y_step, f"• {text}", fontsize=9, 
                       color=DASHBOARD_COLORS['text_primary'], transform=ax.transAxes)
    
    def _draw_additional_metrics_section(self, fig, additional_metrics: Dict[str, float]):
        """Рисует секцию дополнительных метрик в 2 ряда (8 метрик)"""
        # Создаём область для метрик (2 ряда по 4 метрики) - нижняя граница прижата к футеру
        gs = fig.add_gridspec(2, 4, wspace=0.05, hspace=0.15,
                              left=0.02, right=0.98, top=0.18, bottom=0.03,
                              figure=fig)
        
        # Все метрики (8 штук: 5 из спецификации + 3 дополнительных)
        metrics_info = [
            ('stability', 'Стабильность', 'контроль положения тела'),
            ('exhaustion', 'Истощение', 'усталость к финишу'),
            ('arm_efficiency', 'Руки', '% нагрузки на руки'),
            ('leg_efficiency', 'Ноги', '% нагрузки на ноги'),
            ('recovery', 'Восстановление', 'качество отдыха'),
            ('productivity', 'Продуктивность', 'эффект/затраты'),
            ('economy', 'Экономичность', 'минимум лишних движений'),
            ('balance', 'Баланс', 'центр масс относительно опоры'),
        ]
        
        for i, (key, name, hint) in enumerate(metrics_info):
            row = i // 4  # Первый ряд: 0-3, второй ряд: 4-7
            col = i % 4   # Колонка: 0-3
            ax = fig.add_subplot(gs[row, col])
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.axis('off')
            
            value = additional_metrics.get(key, 0)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                value = 0.0
            value = max(0.0, min(100.0, float(value)))
            
            # Цвет по значению (истощение — инвертированная логика)
            if key == 'exhaustion':
                if value <= 30:
                    color = DASHBOARD_COLORS['excellent']
                elif value <= 50:
                    color = DASHBOARD_COLORS['medium']
                else:
                    color = DASHBOARD_COLORS['poor']
            else:
                if value >= 70:
                    color = DASHBOARD_COLORS['excellent']
                elif value >= 50:
                    color = DASHBOARD_COLORS['medium']
                else:
                    color = DASHBOARD_COLORS['poor']
            
            # Значение (большое) - смещено выше
            ax.text(50, 80, f'{int(value)}%', fontsize=24, fontweight='bold',
                   color=color, ha='center', va='center')
            
            # Название - увеличен отступ еще больше
            ax.text(50, 55, name, fontsize=10, 
                   color=DASHBOARD_COLORS['text_primary'], 
                   ha='center', va='center')
            
            # Короткое описание - смещено ниже с большим отступом
            ax.text(50, 35, hint, fontsize=11, 
                   color=DASHBOARD_COLORS['text_secondary'], 
                   ha='center', va='center')
            
            # Для рук/ног добавляем пояснение о норме - смещено еще ниже
            if key == 'arm_efficiency':
                arm_load = additional_metrics.get('arm_efficiency', value)
                if isinstance(arm_load, dict):
                    arm_load = arm_load.get('arm_load', value)
                norm_text = f"(норма 30-40%)" if arm_load > 50 else f"(норма 30-40%) ✓"
                ax.text(50, 18, norm_text, fontsize=9, 
                       color=DASHBOARD_COLORS['text_secondary'], 
                       ha='center', va='center')
            elif key == 'leg_efficiency':
                leg_load = additional_metrics.get('leg_efficiency', value)
                if isinstance(leg_load, dict):
                    leg_load = leg_load.get('leg_load', value)
                norm_text = f"(норма 60-70%)" if leg_load < 60 else f"(норма 60-70%) ✓"
                ax.text(50, 18, norm_text, fontsize=9, 
                       color=DASHBOARD_COLORS['text_secondary'], 
                       ha='center', va='center')
    
    def _draw_additional_metrics(self, ax, analysis_data: Dict[str, Any]):
        """Рисует дополнительные метрики (старая версия для обратной совместимости)"""
        additional_metrics = analysis_data.get('additional_metrics', {})
        if not additional_metrics:
            ax.text(0.5, 0.5, 'Дополнительные метрики недоступны', 
                   ha='center', va='center', fontsize=14, 
                   color=DASHBOARD_COLORS['text_primary'], transform=ax.transAxes)
            return
        
        # Заголовок
        ax.text(0.5, 0.95, '📈 Дополнительные показатели', fontsize=16, 
               color=DASHBOARD_COLORS['text_primary'], 
               fontweight='bold', ha='center', transform=ax.transAxes)
        
        # Метрики
        metrics_names = {
            'stability': ('Стабильность', 'контроль тела'),
            'exhaustion': ('Истощение', 'усталость к финишу'),
            'arm_efficiency': ('Руки', '% нагрузки'),
            'leg_efficiency': ('Ноги', '% нагрузки'),
            'recovery': ('Восстановление', 'качество отдыха')
        }
        
        y_start = 0.75
        y_step = 0.15
        x_left = 0.1
        x_right = 0.6
        
        for i, (key, (name, hint)) in enumerate(metrics_names.items()):
            value = additional_metrics.get(key, 0)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                value = 0.0
            value = max(0.0, min(100.0, float(value)))
            
            y_pos = y_start - i * y_step
            
            # Цвет по значению
            if value >= 70:
                color = DASHBOARD_COLORS['excellent']
            elif value >= 50:
                color = DASHBOARD_COLORS['medium']
            else:
                color = DASHBOARD_COLORS['poor']
            
            # Название и значение
            ax.text(x_left, y_pos, name, fontsize=12, 
                   color=DASHBOARD_COLORS['text_primary'], transform=ax.transAxes)
            ax.text(x_right, y_pos, f'{int(value)}%', fontsize=16, color=color, 
                   fontweight='bold', transform=ax.transAxes)
            ax.text(x_left, y_pos - 0.05, hint, fontsize=9, 
                   color=DASHBOARD_COLORS['text_secondary'], transform=ax.transAxes)
    
    def _draw_footer(self, fig):
        """
        Отрисовка footer с методологией и таймстампом.
        """
        # УБРАНО: разделительная линия
        
        # Методология (слева) - прижата к низу
        methodology_text = (
            "Методология: Eric J. Hörst «Training for Climbing» · "
            "Self-Coached Climber · Movement for Climbers"
        )
        fig.text(0.05, 0.01, methodology_text, 
                 fontsize=8, color=DASHBOARD_COLORS['text_muted'], ha='left',
                 transform=fig.transFigure)
        
        # Таймстамп (справа) - прижат к низу
        timestamp = datetime.now().strftime("%d.%m.%Y, %H:%M")
        fig.text(0.95, 0.01, f"Сгенерировано: {timestamp}", 
                 fontsize=8, color=DASHBOARD_COLORS['text_muted'], ha='right',
                 transform=fig.transFigure)
    
    def _draw_summary_stats(self, ax, analysis_data: Dict[str, Any]):
        """Рисует общую статистику (старая версия для обратной совместимости)"""
        ax.set_facecolor(DASHBOARD_COLORS['background'])
        ax.axis('off')
        
        # Собираем статистику
        stats = []
        
        # Длительность
        duration = analysis_data.get('duration', 0)
        stats.append(('Длительность', f'{duration:.1f} сек'))
        
        # Качество позы
        avg_quality = analysis_data.get('avg_pose_quality', 0)
        stats.append(('Качество позы', f'{avg_quality:.1f}%'))
        
        # Интенсивность движения
        avg_intensity = analysis_data.get('avg_motion_intensity', 0)
        stats.append(('Интенсивность', f'{avg_intensity:.1f}'))
        
        # Падение
        fall_detected = analysis_data.get('fall_detected', False)
        stats.append(('Падение', 'Да' if fall_detected else 'Нет'))
        
        # Общая оценка из техники
        technique_metrics = analysis_data.get('technique_metrics', {})
        if technique_metrics:
            valid_values = [v for v in technique_metrics.values() 
                          if isinstance(v, (int, float)) and not math.isnan(v)]
            if valid_values:
                avg_score = sum(valid_values) / len(valid_values)
                stats.append(('Общая оценка', f'{avg_score:.1f}%'))
        
        # Оценка уровня
        estimated_grade = analysis_data.get('estimated_grade', None)
        if estimated_grade:
            stats.append(('Уровень сложности', estimated_grade))
        
        # Рисуем статистику
        y_start = 0.9
        y_step = 0.15
        
        ax.text(0.1, 0.95, 'Общая статистика', fontsize=18, 
               color=DASHBOARD_COLORS['text_primary'], 
               fontweight='bold', transform=ax.transAxes)
        
        for i, (label, value) in enumerate(stats):
            y_pos = y_start - i * y_step
            ax.text(0.1, y_pos, f'{label}:', fontsize=14, 
                   color=DASHBOARD_COLORS['text_secondary'], transform=ax.transAxes)
            ax.text(0.6, y_pos, str(value), fontsize=14, 
                   color=DASHBOARD_COLORS['text_primary'], 
                   fontweight='bold', transform=ax.transAxes)
    
    def _extract_metrics(self, analysis_data: Dict[str, Any]) -> Dict[str, float]:
        """Извлекает метрики из данных анализа"""
        metrics = {}
        
        # Пытаемся вычислить из доступных данных
        avg_quality = analysis_data.get('avg_pose_quality', 50)
        avg_intensity = analysis_data.get('avg_motion_intensity', 50)
        balance_score = analysis_data.get('avg_balance_score', 50)
        
        metrics['сила'] = min(100, max(0, avg_quality * 0.8))
        metrics['баланс'] = min(100, max(0, balance_score))
        metrics['координация'] = min(100, max(0, 100 - abs(avg_intensity - 40)))
        metrics['техника'] = min(100, max(0, (avg_quality + balance_score) / 2))
        
        return metrics
