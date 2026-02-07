# Дополнение к спецификации — недостающие элементы

**Версия:** 1.1  
**Статус:** Доработка до 100%

---

## 1. Полный парсер TEXT_TEMPLATES.md

Заменить упрощённый парсер на полноценный:

```python
# app/analysis/template_parser.py

import re
from pathlib import Path
from typing import Dict, Any, Optional

class TemplateParser:
    """Парсер шаблонов из TEXT_TEMPLATES.md"""
    
    def __init__(self, template_path: str = "files/TEXT_TEMPLATES.md"):
        self.template_path = Path(template_path)
        self.templates: Dict[str, Dict] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Загрузка и парсинг шаблонов из Markdown файла"""
        if not self.template_path.exists():
            print(f"⚠️ Файл шаблонов не найден: {self.template_path}")
            self._load_defaults()
            return
        
        content = self.template_path.read_text(encoding='utf-8')
        
        # Парсим Python-словари из Markdown
        self._parse_metric_templates(content)
        self._parse_swot_templates(content)
        self._parse_grade_estimation(content)
    
    def _parse_metric_templates(self, content: str):
        """Извлечение шаблонов метрик"""
        # Паттерн для извлечения Python dict из ```python ... ```
        pattern = r'(\w+_TEMPLATES)\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        
        matches = re.findall(pattern, content, re.DOTALL)
        
        for name, body in matches:
            try:
                # Безопасный парсинг словаря
                template_dict = self._safe_eval_dict('{' + body + '}')
                metric_name = name.replace('_TEMPLATES', '').lower()
                self.templates[metric_name] = template_dict
            except Exception as e:
                print(f"⚠️ Ошибка парсинга {name}: {e}")
    
    def _safe_eval_dict(self, dict_str: str) -> Dict:
        """Безопасный парсинг строки словаря"""
        # Заменяем Python-специфичные конструкции
        dict_str = re.sub(r'#.*$', '', dict_str, flags=re.MULTILINE)  # удаляем комментарии
        
        # Используем ast.literal_eval для безопасности
        import ast
        try:
            return ast.literal_eval(dict_str)
        except:
            # Fallback: простой парсинг ключ-значение
            return self._manual_parse(dict_str)
    
    def _manual_parse(self, dict_str: str) -> Dict:
        """Ручной парсинг если ast не справился"""
        result = {}
        
        # Ищем паттерны "key": "value" или "key": {nested}
        key_pattern = r'"(\w+)":\s*"([^"]*)"'
        for match in re.finditer(key_pattern, dict_str):
            result[match.group(1)] = match.group(2)
        
        return result
    
    def _parse_swot_templates(self, content: str):
        """Извлечение SWOT шаблонов"""
        # Ищем THREAT_TEMPLATES и OPPORTUNITY_TEMPLATES
        for template_name in ['THREAT_TEMPLATES', 'OPPORTUNITY_TEMPLATES']:
            pattern = rf'{template_name}\s*=\s*\{{([^}}]+(?:\{{[^}}]*\}}[^}}]*)*)\}}'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    template_dict = self._safe_eval_dict('{' + match.group(1) + '}')
                    self.templates[template_name.lower()] = template_dict
                except Exception as e:
                    print(f"⚠️ Ошибка парсинга {template_name}: {e}")
    
    def _parse_grade_estimation(self, content: str):
        """Извлечение таблицы оценки уровня"""
        pattern = r'GRADE_ESTIMATION\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                self.templates['grade_estimation'] = self._safe_eval_dict('{' + match.group(1) + '}')
            except Exception as e:
                print(f"⚠️ Ошибка парсинга GRADE_ESTIMATION: {e}")
    
    def _load_defaults(self):
        """Загрузка дефолтных шаблонов (текущая реализация)"""
        # Текущие дефолтные шаблоны остаются как fallback
        pass
    
    def get_template(self, metric_name: str, level: str) -> Optional[Dict]:
        """Получить шаблон для метрики и уровня"""
        metric_templates = self.templates.get(metric_name, {})
        return metric_templates.get(level)
    
    def get_text(self, metric_name: str, score: float, raw_data: Dict) -> Dict[str, str]:
        """Получить готовые тексты для метрики"""
        # Определяем уровень
        if score >= 75:
            level = "excellent"
        elif score >= 60:
            level = "good"
        elif score >= 45:
            level = "medium"
        else:
            level = "poor"
        
        template = self.get_template(metric_name, level)
        if not template:
            return {}
        
        # Подставляем значения
        result = {}
        for key, text in template.items():
            if isinstance(text, str):
                try:
                    result[key] = text.format(score=int(score), **raw_data)
                except KeyError as e:
                    result[key] = text  # Возвращаем без подстановки если ключ не найден
        
        return result


# Использование в swot_generator.py:
# 
# from app.analysis.template_parser import TemplateParser
# 
# class SWOTGenerator:
#     def __init__(self):
#         self.parser = TemplateParser("files/TEXT_TEMPLATES.md")
#     
#     def get_strength_text(self, metric_name, data):
#         texts = self.parser.get_text(metric_name, data["score"], data["raw"])
#         return texts.get("strength", "")
```

---

## 2. Дашборд: список метрик с прогресс-барами

Добавить в `app/reports/dashboard.py` новый метод:

```python
def _draw_metrics_list(self, ax, technique_metrics: Dict):
    """
    Отрисовка списка метрик с прогресс-барами.
    
    Располагается слева от паутинки в Technique Section.
    """
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    # Названия метрик с пояснениями
    metrics_info = [
        ("quiet_feet", "Quiet Feet", "Точность постановки ног"),
        ("hip_position", "Hip Position", "Положение таза у стены"),
        ("diagonal", "Противовес", "Диагональная координация"),
        ("route_reading", "Считывание", "Планирование маршрута"),
        ("rhythm", "Ритм", "Равномерность темпа"),
        ("dynamic_control", "Динамика", "Контроль после бросков"),
        ("grip_release", "Grip Release", "Плавность перехватов"),
    ]
    
    y_start = 95
    y_step = 13
    bar_height = 4
    bar_width = 60
    x_label = 5
    x_bar = 35
    x_score = 97
    
    for i, (key, name, hint) in enumerate(metrics_info):
        y = y_start - i * y_step
        
        # Получаем значение метрики
        score = technique_metrics.get(key, {}).get("score", 0)
        if score is None:
            score = 0
        
        # Определяем цвет
        if score >= 75:
            color = '#00ff88'  # зелёный
            level = "отлично"
        elif score >= 60:
            color = '#88ff00'  # салатовый
            level = "хорошо"
        elif score >= 45:
            color = '#ffcc00'  # жёлтый
            level = "средне"
        else:
            color = '#ff6b6b'  # красный
            level = "слабо"
        
        # Название метрики
        ax.text(x_label, y + 2, name, fontsize=9, fontweight='bold',
                color='white', va='center')
        
        # Подсказка
        ax.text(x_label, y - 2, hint, fontsize=7, color='#888888', va='center')
        
        # Фон прогресс-бара
        bar_bg = plt.Rectangle((x_bar, y - bar_height/2), bar_width, bar_height,
                                facecolor='#333333', edgecolor='none')
        ax.add_patch(bar_bg)
        
        # Заполнение прогресс-бара
        fill_width = bar_width * (score / 100)
        bar_fill = plt.Rectangle((x_bar, y - bar_height/2), fill_width, bar_height,
                                  facecolor=color, edgecolor='none')
        ax.add_patch(bar_fill)
        
        # Значение справа
        ax.text(x_score, y, f"{int(score)}%", fontsize=9, fontweight='bold',
                color=color, va='center', ha='right')


def _create_technique_section(self, fig, technique_metrics: Dict, overall_score: float, grade: str):
    """
    Создание секции техники с паутинкой И списком метрик.
    """
    # Создаём gridspec для двух колонок
    gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=0.1,
                          left=0.05, right=0.95, top=0.85, bottom=0.55)
    
    # Левая колонка: список метрик
    ax_list = fig.add_subplot(gs[0, 0])
    self._draw_metrics_list(ax_list, technique_metrics)
    
    # Правая колонка: паутинка
    ax_spider = fig.add_subplot(gs[0, 1], projection='polar')
    self._draw_spider_chart(ax_spider, technique_metrics)
    
    # Общий балл и уровень под паутинкой
    fig.text(0.75, 0.52, f"Общий балл: {int(overall_score)}/100", 
             fontsize=12, fontweight='bold', color='white', ha='center')
    fig.text(0.75, 0.48, f"Уровень: {grade}", 
             fontsize=11, color='#00d4ff', ha='center')
```

---

## 3. Дашборд: Footer с методологией

Добавить в конец `generate_dashboard()`:

```python
def _draw_footer(self, fig):
    """
    Отрисовка footer с методологией и таймстампом.
    """
    from datetime import datetime
    
    # Разделительная линия
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.08, 0.08], 
                               color='#333333', linewidth=1,
                               transform=fig.transFigure))
    
    # Методология (слева)
    methodology_text = (
        "Методология: Eric J. Hörst «Training for Climbing» · "
        "Self-Coached Climber · Movement for Climbers"
    )
    fig.text(0.05, 0.04, methodology_text, 
             fontsize=8, color='#666666', ha='left',
             transform=fig.transFigure)
    
    # Таймстамп (справа)
    timestamp = datetime.now().strftime("%d.%m.%Y, %H:%M")
    fig.text(0.95, 0.04, f"Сгенерировано: {timestamp}", 
             fontsize=8, color='#666666', ha='right',
             transform=fig.transFigure)


# Вызвать в конце generate_dashboard():
# self._draw_footer(fig)
```

---

## 4. Обновлённая структура generate_dashboard()

```python
def generate_dashboard(self, analysis_result: Dict) -> str:
    """
    Генерация полного дашборда согласно dashboard_prototype.html
    """
    # Создаём фигуру
    fig = plt.figure(figsize=(12, 16), facecolor='#1a1a2e')
    
    # === HEADER ===
    self._draw_header(fig, analysis_result)
    
    # === TECHNIQUE SECTION (паутинка + список метрик) ===
    technique_metrics = analysis_result.get('technique_metrics', {})
    overall_score = analysis_result.get('technique_overall_score', 0)
    grade = analysis_result.get('estimated_grade', 'N/A')
    self._create_technique_section(fig, technique_metrics, overall_score, grade)
    
    # === SWOT GRID ===
    swot = analysis_result.get('swot', {})
    self._draw_swot_grid(fig, swot)
    
    # === ADDITIONAL METRICS ===
    additional = analysis_result.get('additional_metrics', {})
    self._draw_additional_metrics(fig, additional)
    
    # === FOOTER ===
    self._draw_footer(fig)
    
    # Сохраняем
    output_path = self._get_output_path()
    fig.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#1a1a2e', edgecolor='none')
    plt.close(fig)
    
    return output_path
```

---

## 5. Полная структура дашборда (координаты)

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (top=0.98, bottom=0.92)                             │
│  ClimbAI BoulderVision | Дата | Время | Кадры               │
├─────────────────────────────────────────────────────────────┤
│  TECHNIQUE SECTION (top=0.90, bottom=0.55)                  │
│  ┌─────────────────────┬───────────────────┐                │
│  │ Список метрик       │    Паутинка       │                │
│  │ с прогресс-барами   │    7 осей         │                │
│  │ (7 строк)           │                   │                │
│  │                     │  Score: 66        │                │
│  │                     │  Уровень: 6a-6b   │                │
│  └─────────────────────┴───────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│  SWOT GRID (top=0.52, bottom=0.22)                          │
│  ┌─────────────┬─────────────┐                              │
│  │ STRENGTHS   │ WEAKNESSES  │                              │
│  │ (зелёный)   │ (жёлтый)    │                              │
│  ├─────────────┼─────────────┤                              │
│  │ OPPORTUNIT. │ THREATS     │                              │
│  │ (синий)     │ (красный)   │                              │
│  └─────────────┴─────────────┘                              │
├─────────────────────────────────────────────────────────────┤
│  ADDITIONAL METRICS (top=0.18, bottom=0.10)                 │
│  Стабильность | Истощение | Руки | Ноги | Восстановление   │
├─────────────────────────────────────────────────────────────┤
│  FOOTER (top=0.08, bottom=0.02)                             │
│  Методология: Eric J. Hörst...  |  Сгенерировано: дата     │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Цвета (согласно dashboard_prototype.html)

```python
DASHBOARD_COLORS = {
    # Фон
    "background": "#1a1a2e",
    "card_bg": "rgba(255, 255, 255, 0.03)",
    
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
    
    # SWOT карточки
    "strengths_border": "rgba(0, 255, 136, 0.3)",
    "strengths_bg": "rgba(0, 255, 136, 0.05)",
    "weaknesses_border": "rgba(255, 204, 0, 0.3)",
    "weaknesses_bg": "rgba(255, 204, 0, 0.05)",
    "opportunities_border": "rgba(0, 212, 255, 0.3)",
    "opportunities_bg": "rgba(0, 212, 255, 0.05)",
    "threats_border": "rgba(255, 107, 107, 0.3)",
    "threats_bg": "rgba(255, 107, 107, 0.05)",
}
```

---

## Чеклист для Cursor

После применения этих дополнений:

- [ ] Создать `app/analysis/template_parser.py`
- [ ] Обновить `SWOTGenerator` для использования `TemplateParser`
- [ ] Добавить `_draw_metrics_list()` в `dashboard.py`
- [ ] Добавить `_create_technique_section()` в `dashboard.py`
- [ ] Добавить `_draw_footer()` в `dashboard.py`
- [ ] Обновить `generate_dashboard()` с новой структурой
- [ ] Проверить все координаты и отступы
- [ ] Тест: сгенерировать дашборд и сравнить с `dashboard_prototype.html`

---

**После этих изменений функционал будет 100%**
