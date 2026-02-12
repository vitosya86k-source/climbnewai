"""
SWOT-анализатор на основе метрик и текстовых шаблонов

Генерирует SWOT-анализ без использования ИИ, используя шаблоны из TEXT_TEMPLATES.md
"""

import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
import ast
import re

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = {
    'strengths': 75,
    'weaknesses': 55,
}

ADVANCED_THRESHOLDS = {
    'quiet_feet': {'weaknesses': 40, 'strengths': 80},
    'rhythm': {'weaknesses': 45},
    'route_reading': {'weaknesses': 40},
}

ADVANCED_TEXT_OVERRIDES = {
    'quiet_feet': {
        'medium': {
            'weakness': (
                "Работа ног {score}% — есть пространство для повышения точности постановки. "
                "На вашем уровне это тонкая настройка."
            ),
        },
        'poor': {
            'weakness': (
                "Точность постановки ног {score}% — ниже ожидаемого для вашего уровня. "
                "Стоит добавить осознанность в работе стоп."
            ),
        },
    },
    'rhythm': {
        'medium': {
            'weakness': (
                "Ритм {score}% — на сложных участках темп неравномерный. "
                "Для вашей категории это часто норма, но выровненный ритм даст экономию."
            ),
        },
    },
}

ADVANCED_OPPORTUNITY_OVERRIDES = {
    'quiet_feet': (
        "Повышение точности постановки ног — тонкий резерв экономии. "
        "На вашем уровне это добавит запас на длинных и силовых маршрутах."
    ),
}

# Пытаемся импортировать новый парсер
try:
    from app.analysis.template_parser import TemplateParser
    TEMPLATE_PARSER_AVAILABLE = True
except ImportError:
    TEMPLATE_PARSER_AVAILABLE = False
    logger.warning("TemplateParser не доступен, используем дефолтные шаблоны")


class SWOTGenerator:
    """Генератор SWOT-анализа на основе метрик и шаблонов"""
    
    def __init__(self, templates_path: Optional[Path] = None):
        """
        Args:
            templates_path: путь к файлу TEXT_TEMPLATES.md (если None, использует дефолтные шаблоны)
        """
        self.templates_path = templates_path or Path(__file__).parent.parent.parent / "files" / "TEXT_TEMPLATES.md"
        
        # Используем новый парсер если доступен
        if TEMPLATE_PARSER_AVAILABLE:
            try:
                self.parser = TemplateParser(self.templates_path)
                self.templates = self.parser.templates if self.parser.templates else self._get_default_templates()
                logger.info(f"✅ Используется TemplateParser для загрузки шаблонов")
            except Exception as e:
                logger.warning(f"Ошибка инициализации TemplateParser: {e}, используем дефолтные шаблоны")
                self.parser = None
                self.templates = self._load_templates()
        else:
            self.parser = None
            self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Any]:
        """Загрузка шаблонов из файла"""
        try:
            if self.templates_path.exists():
                # Парсим Markdown файл с шаблонами
                # Упрощенная версия - в реальности нужен более сложный парсер
                templates = self._parse_templates_file()
                logger.info(f"Загружено шаблонов из {self.templates_path}")
                return templates
            else:
                logger.warning(f"Файл шаблонов не найден: {self.templates_path}, используем дефолтные")
                return self._get_default_templates()
        except Exception as e:
            logger.error(f"Ошибка загрузки шаблонов: {e}", exc_info=True)
            return self._get_default_templates()
    
    def _parse_templates_file(self) -> Dict[str, Any]:
        """Парсинг файла TEXT_TEMPLATES.md"""
        # Упрощенная версия - в реальности нужен полноценный парсер Markdown
        # Пока используем дефолтные шаблоны
        return self._get_default_templates()
    
    def _get_default_templates(self) -> Dict[str, Any]:
        """Дефолтные шаблоны на основе TEXT_TEMPLATES.md"""
        return {
            'quiet_feet': {
                'excellent': {
                    'strength': "Точные ноги {score}% — ставите ногу сразу в нужное место, экономите энергию."
                },
                'good': {
                    'strength': "Работа ног {score}% — редкие перестановки, это экономит силы."
                },
                'medium': {
                    'weakness': "Перестановки ног {score}% — {repositions} движений на зацепку вместо {norm}. Съедает энергию."
                },
                'poor': {
                    'weakness': "Ноги «ищут» зацепку — {score}%. {repositions} перестановок вместо {norm}. Критично для прогресса."
                }
            },
            'hip_position': {
                'excellent': {
                    'strength': "Положение таза {score}% — вес на ногах, руки отдыхают. Отличная техника."
                },
                'good': {
                    'strength': "Положение таза {score}% — небольшое отклонение, но в целом хорошо."
                },
                'medium': {
                    'weakness': "Таз отклонён — {score}% ({angle}°). Руки несут лишние {overload}% веса."
                },
                'poor': {
                    'weakness': "Таз далеко от стены — {score}% ({angle}°). Руки перегружены на {overload}%. Главная точка роста."
                }
            },
            'diagonal': {
                'excellent': {
                    'strength': "Противовес {score}% — отличная диагональная работа, баланс стабильный."
                },
                'good': {
                    'strength': "Противовес {score}% — диагональ работает, баланс хороший."
                },
                'medium': {
                    'weakness': "Противовес {score}% — движения «квадратом», тело раскачивается."
                },
                'poor': {
                    'weakness': "Нет диагонали — {score}%. Хаотичные движения, много энергии на стабилизацию."
                }
            },
            'route_reading': {
                'excellent': {
                    'strength': "Считывание {score}% — планируете маршрут, делаете паузы. Признак опытного скалолаза."
                },
                'good': {
                    'strength': "Считывание {score}% — есть планирование, не лезете вслепую."
                },
                'medium': {
                    'weakness': "Считывание {score}% — мало пауз для просмотра. Добавьте планирование."
                },
                'poor': {
                    'weakness': "Импульсивное лазание — {score}%. Бросаетесь на маршрут без плана."
                }
            },
            'rhythm': {
                'excellent': {
                    'strength': "Ритм {score}% — движения равномерные, полный контроль."
                },
                'good': {
                    'strength': "Ритм {score}% — темп стабильный, небольшие колебания."
                },
                'medium': {
                    'weakness': "Ритм {score}% — темп сбивается на сложных участках. Разброс ±{variance}мс."
                },
                'poor': {
                    'weakness': "Рваный ритм — {score}%. Разброс ±{variance}мс. Признак стресса или паники."
                }
            },
            'dynamic_control': {
                'excellent': {
                    'strength': "Контроль динамики {score}% — после бросков сразу стабилизируетесь."
                },
                'good': {
                    'strength': "Контроль динамики {score}% — динамические ходы под контролем."
                },
                'medium': {
                    'weakness': "Контроль динамики {score}% — после бросков долго «ловите» баланс ({time}с)."
                },
                'poor': {
                    'weakness': "Теряете контроль после бросков — {score}%. Стабилизация {time}с вместо 0.5с."
                }
            },
            'grip_release': {
                'excellent': {
                    'strength': "Перехваты {score}% — плавные, мягкие движения. Экономия энергии."
                },
                'good': {
                    'strength': "Перехваты {score}% — достаточно плавные движения рук."
                },
                'medium': {
                    'weakness': "Перехваты {score}% — рывки при отпускании, теряете баланс."
                },
                'poor': {
                    'weakness': "Резкие перехваты — {score}%. Дёргаете зацепы, теряете баланс и энергию."
                }
            },
            'stability': {
                'excellent': {
                    'strength': "Стабильность {score}% — тело не «гуляет», минимум лишних движений."
                },
                'good': {
                    'strength': "Стабильность {score}% — хороший контроль положения."
                },
                'medium': {
                    'weakness': "Стабильность {score}% — тело «гуляет», много микрокоррекций."
                },
                'poor': {
                    'weakness': "Стабильность {score}% — много энергии на удержание равновесия."
                }
            },
            'arm_efficiency': {
                'medium': {
                    'weakness': "Руки перегружены — {arm_load}% вместо 30-40%. Переносите вес на ноги."
                },
                'poor': {
                    'weakness': "Руки {arm_load}% — критический перегруз. Техника требует работы."
                }
            },
            'leg_efficiency': {
                'medium': {
                    'weakness': "Ноги только {leg_load}% — недогружены. Активнее толкайтесь."
                },
                'poor': {
                    'weakness': "Ноги {leg_load}% — почти не работают. Главная точка роста."
                }
            },
            'recovery': {
                'excellent': {
                    'strength': "Восстановление {score}% — умеете находить позы для отдыха и вытряхивать руки."
                },
                'good': {
                    'strength': "Восстановление {score}% — делаете паузы, даёте рукам отдых."
                },
                'medium': {
                    'weakness': "Восстановление {score}% — редкие паузы или отдых неэффективен."
                },
                'poor': {
                    'weakness': "Не отдыхаете — {score}%. Лезете на износ без пауз."
                }
            },
            'opportunities': {
                'hip_position': "Если улучшить положение таза до {target}% — руки будут уставать на {reduction}% меньше.",
                'quiet_feet': "Работа над точностью ног уберёт {saved} лишних движений за маршрут — экономия {energy}% энергии.",
                'grip_release': "Плавные перехваты — это +1 категория сложности. Сейчас это ваш потолок.",
                'leg_activation': "Ноги несут только {current}% веса. Если довести до 65% — откроются нависания.",
                'rhythm': "Ровный ритм снизит расход энергии на {saved}% и уберёт панику на сложных участках.",
                'recovery': "Научитесь отдыхать на маршруте — сможете лезть длиннее на {time}% времени."
            },
            'threats': {
                'shoulder': "{side} плечо — зажим в {count} точках маршрута. Если паттерн сохранится, плечо начнёт ограничивать амплитуду. Обратите внимание на расслабление при перехватах.",
                'elbow': "{side} локоть — частые острые углы под нагрузкой. Со временем это снизит силу хвата и комфорт на длинных маршрутах. Обратите внимание на выпрямление рук в промежуточных позициях.",
                'knee_rotation': "{side} колено — ротация под нагрузкой {count} раз за пролаз. Такой паттерн постепенно снижает стабильность на «флагах» и накатках. Обратите внимание на постановку стопы перед нагрузкой.",
                'lower_back': "Поясница — скручивание {angle}° под нагрузкой. При регулярном повторении это ограничит контроль на нависаниях. Обратите внимание на включение кора перед силовыми ходами.",
                'exhaustion_critical': "Истощение {percent}% — последняя часть маршрута в красной зоне. Контроль падает, движения становятся случайными. Обратите внимание на паузы для восстановления до финишной секции.",
                'overtraining': "Паттерн указывает на накопленную усталость: техника деградирует от попытки к попытке. Обратите внимание — сейчас отдых даст больше прогресса, чем ещё один подход.",
                'productivity_decline': "Продуктивность падает на {drop}% во второй половине маршрута — движения перестают приближать к цели. Обратите внимание: это сигнал пересмотреть тактику прохождения, а не «долезать на характере».",
                'economy_drain': "Расход энергии в {ratio}× выше нормы — на маршрутах длиннее {max_moves} ходов запас закончится раньше топа. Обратите внимание на лишние движения в средней части маршрута.",
                'balance_compensation': "Компенсация баланса руками в {count} точках — предплечья устают быстрее, чем должны. Обратите внимание на перенос веса на ноги перед каждым перехватом."
            }
        }
    
    def generate_swot(
        self,
        technique_metrics: Dict[str, float],
        additional_metrics: Dict[str, float],
        tension_data: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Генерация SWOT-анализа
        
        Args:
            technique_metrics: 7 базовых метрик техники
            additional_metrics: дополнительные метрики
            tension_data: данные о зонах напряжения
            raw_data: сырые данные для подстановки в шаблоны
            
        Returns:
            dict с ключами: strengths, weaknesses, opportunities, threats
        """
        swot = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': []
        }
        
        raw_data = self._build_raw_data(
            technique_metrics=technique_metrics,
            additional_metrics=additional_metrics,
            tension_data=tension_data,
            raw_data=raw_data or {}
        )
        estimated_grade = str(raw_data.get('estimated_grade') or raw_data.get('grade') or "")
        
        # === STRENGTHS (метрики >= 75%) ===
        all_metrics = {**technique_metrics, **additional_metrics}
        
        for metric_name, score in all_metrics.items():
            strength_threshold = self._get_threshold(metric_name, 'strengths', estimated_grade)
            if score >= strength_threshold:
                text = self._get_text_for_metric(metric_name, score, 'strength', raw_data, estimated_grade)
                if text:
                    swot['strengths'].append({
                        'metric': metric_name,
                        'score': score,
                        'text': text
                    })
        
        # === WEAKNESSES (метрики < 55%) ===
        for metric_name, score in all_metrics.items():
            weakness_threshold = self._get_threshold(metric_name, 'weaknesses', estimated_grade)
            if score < weakness_threshold:
                text = self._get_text_for_metric(metric_name, score, 'weakness', raw_data, estimated_grade)
                if text:
                    swot['weaknesses'].append({
                        'metric': metric_name,
                        'score': score,
                        'text': text
                    })
        
        # === OPPORTUNITIES (на основе слабостей) ===
        for weakness in swot['weaknesses']:
            metric_name = weakness['metric']
            opportunity = self._get_opportunity_for_weakness(
                metric_name, weakness, all_metrics, raw_data, estimated_grade
            )
            if opportunity:
                swot['opportunities'].append(opportunity)
        
        # === THREATS (риски травм) ===
        threats = self._analyze_injury_risks(additional_metrics, tension_data, raw_data)
        swot['threats'].extend(threats)
        
        # Если opportunities пусто, пытаемся найти из всех слабых метрик
        if not swot['opportunities']:
            for weakness in swot['weaknesses']:
                opp = self._get_opportunity_for_weakness(
                    weakness['metric'], weakness, all_metrics, raw_data, estimated_grade
                )
                if opp:
                    swot['opportunities'].append(opp)
                    if len(swot['opportunities']) >= 3:
                        break
        
        # Threats уже должны быть заполнены из _analyze_injury_risks
        # Если пусто, добавляем общие риски на основе метрик
        if not swot['threats']:
            # Проверяем критические показатели
            if additional_metrics.get('exhaustion', 0) >= 70:
                swot['threats'].append({
                    'text': f'Истощение {int(additional_metrics.get("exhaustion", 0))}% — последняя часть маршрута в красной зоне. Падение контроля = риск срыва.',
                    'type': 'exhaustion_critical'
                })
            elif additional_metrics.get('exhaustion', 0) >= 50:
                swot['threats'].append({
                    'text': f'Истощение {int(additional_metrics.get("exhaustion", 0))}% — заметное падение качества к финишу.',
                    'type': 'exhaustion'
                })
            
            if additional_metrics.get('stability', 100) < 40:
                swot['threats'].append({
                    'text': f'Стабильность {int(additional_metrics.get("stability", 50))}% — сильная нестабильность, высокие энергозатраты. Риск травм при нестабильных движениях.',
                    'type': 'stability'
                })
            
            # Если все еще пусто, добавляем общую рекомендацию
            if not swot['threats']:
                swot['threats'].append({
                    'text': 'Контролируйте усталость во время длительных сессий. Правильно разминайтесь перед лазанием.',
                    'type': 'general'
                })
        
        # Ограничиваем количество
        swot['strengths'] = swot['strengths'][:4]
        swot['weaknesses'] = swot['weaknesses'][:4]
        swot['opportunities'] = swot['opportunities'][:3]
        swot['threats'] = swot['threats'][:3]
        
        return swot
    
    def _get_text_for_metric(
        self,
        metric_name: str,
        score: float,
        text_type: str,
        raw_data: Dict[str, Any],
        estimated_grade: str = "",
    ) -> Optional[str]:
        """Получение текста для метрики на основе балла из шаблонов TEXT_TEMPLATES.md"""
        # Проверяем наличие шаблона в загруженных шаблонах
        if metric_name not in self.templates:
            logger.debug(f"Шаблон для {metric_name} не найден в загруженных шаблонах")
            return None
        
        templates = self.templates[metric_name]
        
        # Определяем уровень в зависимости от метрики
        # Для exhaustion: low (<30), moderate (30-50), high (50-70), critical (>=70)
        if metric_name == 'exhaustion':
            if score < 30:
                level = 'low'
            elif score < 50:
                level = 'moderate'
            elif score < 70:
                level = 'high'
            else:
                level = 'critical'
        # Для arm_efficiency: optimal (30-40), acceptable (40-50), overloaded (50-65), critical (>65)
        elif metric_name == 'arm_efficiency':
            arm_load = raw_data.get('arm_load', score)
            if 30 <= arm_load <= 40:
                level = 'optimal'
            elif 40 < arm_load <= 50:
                level = 'acceptable'
            elif 50 < arm_load <= 65:
                level = 'overloaded'
            else:
                level = 'critical'
        # Для leg_efficiency: optimal (60-70), good (50-60), underused (40-50), passive (<40)
        elif metric_name == 'leg_efficiency':
            leg_load = raw_data.get('leg_load', score)
            if 60 <= leg_load <= 70:
                level = 'optimal'
            elif 50 <= leg_load < 60:
                level = 'good'
            elif 40 <= leg_load < 50:
                level = 'underused'
            else:
                level = 'passive'
        # Для остальных метрик: excellent (>=75), good (60-74), medium (45-59), poor (<45)
        else:
            if score >= 75:
                level = 'excellent'
            elif score >= 60:
                level = 'good'
            elif score >= 45:
                level = 'medium'
            else:
                level = 'poor'
        
        # Проверяем наличие уровня в шаблонах
        if level not in templates:
            logger.debug(f"Уровень {level} не найден для {metric_name}, доступны: {list(templates.keys())}")
            return None
        
        if level not in templates:
            return None
        
        level_templates = templates[level]
        
        if not isinstance(level_templates, dict):
            return None
        
        if text_type not in level_templates:
            logger.debug(f"Тип текста {text_type} не найден для {metric_name}[{level}]")
            return None
        
        template = level_templates[text_type]
        
        if not isinstance(template, str):
            return None

        if self._is_advanced_grade(estimated_grade):
            metric_overrides = ADVANCED_TEXT_OVERRIDES.get(metric_name, {})
            level_overrides = metric_overrides.get(level, {})
            if text_type in level_overrides:
                template = level_overrides[text_type]
        
        # Подставляем значения
        try:
            # Добавляем score в raw_data если его там нет
            format_data = {'score': int(score), **raw_data}
            text = template.format(**format_data)
            return text
        except KeyError as e:
            logger.warning(f"Отсутствует ключ в raw_data для {metric_name}: {e}, template: {template[:50]}...")
            # Пытаемся подставить только score и доступные ключи
            try:
                # Извлекаем только нужные ключи из шаблона
                import re
                placeholders = re.findall(r'\{(\w+)\}', template)
                format_data = {'score': int(score)}
                for key in placeholders:
                    if key in raw_data:
                        format_data[key] = raw_data[key]
                    elif key == 'score':
                        format_data[key] = int(score)
                text = template.format(**format_data)
                return text
            except Exception as e2:
                logger.warning(f"Не удалось форматировать шаблон для {metric_name}: {e2}")
                return None
    
    def _get_opportunity_for_weakness(
        self,
        metric_name: str,
        weakness: Dict[str, Any],
        all_metrics: Dict[str, float],
        raw_data: Dict[str, Any],
        estimated_grade: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Получение возможности для слабости из шаблонов TEXT_TEMPLATES.md"""
        # Проверяем разные варианты ключей
        opp_templates = None
        if 'opportunity_templates' in self.templates:
            opp_templates = self.templates['opportunity_templates']
        elif 'opportunities' in self.templates:
            opp_templates = self.templates['opportunities']
        
        if not opp_templates:
            return None
        
        if metric_name not in opp_templates:
            return None
        
        template = opp_templates[metric_name]
        if isinstance(template, str):
            template = self._get_opportunity_text(metric_name, estimated_grade, template)
            try:
                text = template.format(**raw_data)
                return {'text': text, 'metric': metric_name}
            except Exception:
                return {'text': template, 'metric': metric_name}
        
        current_score = weakness['score']

        # Переменные для расчётов в формулах и условиях
        variables = dict(raw_data)
        variables.update({
            'score': current_score,
            f'{metric_name}_score': current_score
        })
        if metric_name == 'hip_position':
            variables['hip_score'] = current_score
        if metric_name == 'quiet_feet':
            variables['quiet_feet_score'] = current_score
        if metric_name == 'grip_release':
            variables['grip_score'] = current_score
        if metric_name == 'rhythm':
            variables['rhythm_score'] = current_score
        if metric_name == 'recovery':
            variables['recovery_score'] = current_score

        # Проверяем условие из шаблона
        if 'condition' in template:
            condition = template['condition']
            if not self._check_condition(condition, variables):
                return None
        
        # Рассчитываем значения для подстановки из шаблона
        values = {}
        if 'calculation' in template:
            calc = template['calculation']
            for key, formula in calc.items():
                try:
                    val = self._safe_eval_arith(formula, variables)
                    values[key] = int(val)
                    variables[key] = float(val)
                except Exception as e:
                    logger.warning(f"Ошибка вычисления {key} для {metric_name}: {e}")
        
        # Дополнительные значения из метрик
        if metric_name == 'leg_activation' or metric_name == 'leg_efficiency':
            values['current'] = int(all_metrics.get('leg_efficiency', 50))

        # Контекстные значения для корректной подстановки
        if metric_name == 'quiet_feet':
            repositions = int(raw_data.get('repositions', 1))
            norm = int(raw_data.get('norm', 1))
            values.setdefault('saved', max(1, repositions - norm))
            values.setdefault('energy', int(round(max(5, (100 - weakness['score']) / 2))))
        if metric_name == 'rhythm':
            values.setdefault('saved', int(round(max(5, (100 - weakness['score']) / 2))))
        if metric_name == 'hip_position':
            values.setdefault('target', raw_data.get('target'))
            values.setdefault('reduction', raw_data.get('reduction'))
        if metric_name == 'recovery':
            values.setdefault('time', int(raw_data.get('recovery_time', 10)))
        
        # Если нет расчетов, используем score напрямую
        if not values and 'text' in template:
            values = {'score': int(weakness['score'])}
        
        try:
            text_template = self._get_opportunity_text(metric_name, estimated_grade, template['text'])
            format_data = {**raw_data, **values}
            text = text_template.format(**format_data)
            return {'text': text, 'metric': metric_name}
        except Exception as e:
            logger.warning(f"Ошибка форматирования opportunity для {metric_name}: {e}, values: {values}")
            return None
    
    def _analyze_injury_risks(
        self,
        additional_metrics: Dict[str, float],
        tension_data: Optional[Dict[str, Any]],
        raw_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Анализ рисков травм из шаблонов TEXT_TEMPLATES.md"""
        threats = []
        
        # Проверяем разные варианты ключей
        threat_templates = None
        if 'threat_templates' in self.templates:
            threat_templates = self.templates['threat_templates']
        elif 'threats' in self.templates:
            threat_templates = self.templates['threats']
        
        if not threat_templates:
            return threats
        
        # Проходим по всем шаблонам угроз
        for threat_type, template in threat_templates.items():
            template_text = None
            condition = None
            if isinstance(template, dict):
                template_text = template.get('text')
                condition = template.get('condition')
            elif isinstance(template, str):
                template_text = template

            if not template_text:
                continue
            
            condition_met = False
            
            # Проверяем условие
            try:
                if condition and 'tension_count >= 3' in condition:
                    # Для плеч и других зон напряжения
                    if tension_data:
                        for side in ['left', 'right']:
                            side_key = f'{side}_shoulder'
                            if side_key in tension_data:
                                tension_count = tension_data[side_key].get('high_tension_count', 0)
                                if tension_count >= 3:
                                    condition_met = True
                                    side_name = template.get('side_map', {}).get(side, side) if isinstance(template, dict) else side
                                    text = template_text.format(
                                        side=side_name,
                                        count=tension_count
                                    )
                                    threats.append({'text': text, 'type': threat_type, 'side': side})
                
                elif condition and 'acute_angle_count >= 5' in condition:
                    # Для локтей
                    if tension_data:
                        for side in ['left', 'right']:
                            side_key = f'{side}_elbow'
                            if side_key in tension_data:
                                angle_count = tension_data[side_key].get('acute_angle_count', 0)
                                if angle_count >= 5:
                                    condition_met = True
                                    side_name = template.get('side_map', {}).get(side, side) if isinstance(template, dict) else side
                                    text = template_text.format(side=side_name)
                                    threats.append({'text': text, 'type': threat_type, 'side': side})
                
                elif condition and 'rotation_count >= 2' in condition:
                    # Для коленей
                    if tension_data:
                        for side in ['left', 'right']:
                            side_key = f'{side}_knee'
                            if side_key in tension_data:
                                rotation_count = tension_data[side_key].get('rotation_count', 0)
                                if rotation_count >= 2:
                                    condition_met = True
                                    side_name = template.get('side_map', {}).get(side, side) if isinstance(template, dict) else side
                                    text = template_text.format(side=side_name, count=rotation_count)
                                    threats.append({'text': text, 'type': threat_type, 'side': side})
                
                elif condition and 'twist_angle >= 30' in condition:
                    # Для поясницы
                    if tension_data and 'lower_back' in tension_data:
                        twist_angle = tension_data['lower_back'].get('twist_angle', 0)
                        if twist_angle >= 30:
                            condition_met = True
                            text = template_text.format(angle=int(twist_angle))
                            threats.append({'text': text, 'type': threat_type})
                elif threat_type == 'productivity_decline':
                    productivity = float(additional_metrics.get('productivity', 50))
                    if productivity < 40:
                        drop = int(max(10, (50 - productivity) * 1.2))
                        text = template_text.format(drop=drop)
                        threats.append({'text': text, 'type': threat_type})
                elif threat_type == 'economy_drain':
                    economy = float(additional_metrics.get('economy', 50))
                    if economy < 40:
                        ratio = round(1 + (50 - economy) / 25, 1)
                        max_moves = max(10, int(raw_data.get('hold_count', 30)))
                        text = template_text.format(ratio=ratio, max_moves=max_moves)
                        threats.append({'text': text, 'type': threat_type})
                elif threat_type == 'balance_compensation':
                    balance = float(additional_metrics.get('balance', 50))
                    if balance < 40:
                        count = max(2, int((40 - balance) / 5))
                        text = template_text.format(count=count)
                        threats.append({'text': text, 'type': threat_type})
                
            except Exception as e:
                logger.warning(f"Ошибка проверки условия для {threat_type}: {e}")
        
        return threats

    def _build_raw_data(
        self,
        technique_metrics: Dict[str, float],
        additional_metrics: Dict[str, float],
        tension_data: Optional[Dict[str, Any]],
        raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Заполняет недостающие параметры для шаблонов, вычисляя их из метрик."""
        data = dict(raw_data or {})

        # Базовые метрики
        quiet_feet = float(technique_metrics.get('quiet_feet', 50))
        hip_position = float(technique_metrics.get('hip_position', 50))
        diagonal = float(technique_metrics.get('diagonal', 50))
        route_reading = float(technique_metrics.get('route_reading', 50))
        rhythm = float(technique_metrics.get('rhythm', 50))
        dynamic_control = float(technique_metrics.get('dynamic_control', 50))
        grip_release = float(technique_metrics.get('grip_release', 50))

        # Оценка уровня
        grade = self.estimate_grade(technique_metrics)
        data.setdefault('grade', grade.replace('—', '-'))
        data.setdefault('estimated_grade', grade)

        duration = float(data.get('duration', 60))

        # Quiet Feet: перестановки и норма
        repositions = max(1, int(round(1 + (100 - quiet_feet) / 10)))
        norm = max(1, int(round(1 + (100 - quiet_feet) / 25)))
        data.setdefault('repositions', repositions)
        data.setdefault('norm', norm)
        data.setdefault('times', round(repositions / max(norm, 1), 1))
        data.setdefault('current_repositions', repositions)
        data.setdefault('target_repositions', max(1, repositions - 1))
        data.setdefault('hold_count', max(1, int(round(duration / 2))))

        # Hip Position: угол и перегрузка рук
        angle = int(round(max(5, (100 - hip_position) * 0.6 + 5)))
        overload = int(round(max(0, (100 - hip_position) * 0.8)))
        data.setdefault('angle', angle)
        data.setdefault('overload', overload)
        data.setdefault('target', min(90, int(round(hip_position + 15))))
        data.setdefault('reduction', int(round(max(5, (100 - hip_position) * 0.4))))

        # Route Reading: время перед стартом и паузы
        data.setdefault('start_time', round(1 + (route_reading / 100) * 4, 1))
        data.setdefault('pauses', int(round(route_reading / 30)))

        # Rhythm: разброс темпа
        data.setdefault('variance', int(round(50 + (100 - rhythm) * 3)))
        data.setdefault('saved', int(round(max(5, (100 - rhythm) / 2))))

        # Dynamic control: время стабилизации (секунды)
        data.setdefault('time', round(0.3 + (100 - dynamic_control) / 100 * 1.5, 2))

        # Grip release: экономия энергии (если потребуется)
        data.setdefault('energy', int(round(max(5, (100 - grip_release) / 2))))

        # Дополнительные метрики
        exhaustion = float(additional_metrics.get('exhaustion', 0))
        recovery = float(additional_metrics.get('recovery', 50))
        arm_eff = float(additional_metrics.get('arm_efficiency', 50))

        data.setdefault('percent', int(round(exhaustion)))
        data.setdefault('drop', int(round(exhaustion * 0.6)))
        data.setdefault('exhaustion', exhaustion)

        # Оценка нагрузки на руки/ноги на основе arm_efficiency
        arm_load = int(round(max(20, min(80, 70 - (arm_eff - 50) * 0.6))))
        leg_load = int(round(max(20, min(80, 100 - arm_load))))
        data.setdefault('arm_load', arm_load)
        data.setdefault('leg_load', leg_load)
        data.setdefault('current', leg_load)

        # Восстановление
        data.setdefault('time_gain', int(round(max(1, recovery / 20))))
        data.setdefault('recovery_time', int(round(max(5, recovery / 2))))

        # Потенциал (простая оценка: +1 ступень)
        grade_steps = [
            "до 5a", "5a—5b", "5b—5c", "5c—6a",
            "6a—6b", "6b—6c", "6c—7a", "7a—7b", "7b+"
        ]
        current_idx = grade_steps.index(grade) if grade in grade_steps else 0
        potential_idx = min(len(grade_steps) - 1, current_idx + 1)
        data.setdefault('potential_grade', grade_steps[potential_idx])

        return data

    def _is_advanced_grade(self, estimated_grade: str) -> bool:
        if not estimated_grade:
            return False
        grade_lower = estimated_grade.strip().lower()
        if any(ch in grade_lower for ch in ["7", "8"]):
            return True
        return False

    def _get_threshold(self, metric_name: str, block: str, estimated_grade: str) -> int:
        if self._is_advanced_grade(estimated_grade):
            metric_thresholds = ADVANCED_THRESHOLDS.get(metric_name, {})
            if block in metric_thresholds:
                return metric_thresholds[block]
        return DEFAULT_THRESHOLDS.get(block, 55)

    def _get_opportunity_text(self, metric_name: str, estimated_grade: str, default_text: str) -> str:
        if self._is_advanced_grade(estimated_grade):
            return ADVANCED_OPPORTUNITY_OVERRIDES.get(metric_name, default_text)
        return default_text

    def _safe_eval_arith(self, expr: str, variables: Dict[str, Any]) -> float:
        """Безопасное вычисление простых арифметических выражений с переменными."""
        expr = expr.strip()

        node = ast.parse(expr, mode='eval')

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant):
                return float(n.value)
            if isinstance(n, ast.Num):
                return float(n.n)
            if isinstance(n, ast.Name):
                if n.id in variables:
                    return float(variables[n.id])
                raise ValueError(f"Неизвестная переменная: {n.id}")
            if isinstance(n, ast.BinOp):
                left = _eval(n.left)
                right = _eval(n.right)
                if isinstance(n.op, ast.Add):
                    return left + right
                if isinstance(n.op, ast.Sub):
                    return left - right
                if isinstance(n.op, ast.Mult):
                    return left * right
                if isinstance(n.op, ast.Div):
                    return left / right
                if isinstance(n.op, ast.Pow):
                    return left ** right
                raise ValueError("Недопустимая операция")
            if isinstance(n, ast.UnaryOp):
                val = _eval(n.operand)
                if isinstance(n.op, ast.UAdd):
                    return +val
                if isinstance(n.op, ast.USub):
                    return -val
                raise ValueError("Недопустимая унарная операция")
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                func = n.func.id
                args = [_eval(a) for a in n.args]
                if func == 'min' and len(args) >= 2:
                    return min(args)
                if func == 'max' and len(args) >= 2:
                    return max(args)
                raise ValueError("Недопустимая функция")
            raise ValueError("Недопустимое выражение")

        return float(_eval(node))

    def _check_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Проверка простых условий с AND."""
        parts = [p.strip() for p in condition.split("AND")]
        for part in parts:
            if not part:
                continue
            op = None
            for candidate in ["<=", ">=", "==", "<", ">"]:
                if candidate in part:
                    op = candidate
                    left, right = part.split(candidate, 1)
                    left_val = self._safe_eval_arith(left.strip(), variables)
                    right_val = self._safe_eval_arith(right.strip(), variables)
                    if op == "<=" and not (left_val <= right_val):
                        return False
                    if op == ">=" and not (left_val >= right_val):
                        return False
                    if op == "==" and not (left_val == right_val):
                        return False
                    if op == "<" and not (left_val < right_val):
                        return False
                    if op == ">" and not (left_val > right_val):
                        return False
                    break
            if op is None:
                return False
        return True
    
    def estimate_grade(self, technique_metrics: Dict[str, float]) -> str:
        """
        Оценка уровня сложности на основе метрик техники
        
        Returns:
            строка с диапазоном уровня (например, "6a-6b")
        """
        try:
            from grade_algorithm import estimate_grade as estimate_grade_v2
            grade, _score = estimate_grade_v2(technique_metrics, None)
            return grade
        except Exception:
            pass

        weights = {
            'quiet_feet': 0.20,
            'hip_position': 0.20,
            'diagonal': 0.15,
            'grip_release': 0.15,
            'rhythm': 0.10,
            'dynamic_control': 0.10,
            'route_reading': 0.10
        }
        
        weighted_score = sum(
            technique_metrics.get(m, 50) * w
            for m, w in weights.items()
        )
        
        # Новая таблица соответствия (исправленная)
        grade_table = [
            (85, "7b+"),
            (80, "7a—7b"),
            (75, "6c—7a"),
            (68, "6b—6c"),
            (60, "6a—6b"),
            (50, "5c—6a"),
            (40, "5b—5c"),
            (30, "5a—5b"),
            (0, "до 5a")
        ]
        
        for threshold, grade in grade_table:
            if weighted_score >= threshold:
                return grade
        
        return "до 5a"
