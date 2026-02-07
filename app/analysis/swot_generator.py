"""
SWOT-анализатор на основе метрик и текстовых шаблонов

Генерирует SWOT-анализ без использования ИИ, используя шаблоны из TEXT_TEMPLATES.md
"""

import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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
                'shoulder': "{side} плечо — зажим в {count} точках маршрута. Риск импинджмента при сохранении паттерна.",
                'elbow': "{side} локоть — частые углы <70° под нагрузкой. Риск эпикондилита («локоть скалолаза»).",
                'knee_rotation': "{side} колено — ротация под нагрузкой {count} раз за пролаз. Риск повреждения мениска.",
                'lower_back': "Поясница — скручивание {angle}° под нагрузкой. Риск протрузии при хроническом паттерне.",
                'exhaustion_critical': "Истощение {percent}% — последняя часть маршрута в красной зоне. Падение контроля = риск срыва.",
                'overtraining': "Паттерн указывает на перетренированность: рекомендован отдых или снижение нагрузки."
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
        
        raw_data = raw_data or {}
        
        # === STRENGTHS (метрики >= 75%) ===
        all_metrics = {**technique_metrics, **additional_metrics}
        
        for metric_name, score in all_metrics.items():
            if score >= 75:
                text = self._get_text_for_metric(metric_name, score, 'strength', raw_data)
                if text:
                    swot['strengths'].append({
                        'metric': metric_name,
                        'score': score,
                        'text': text
                    })
        
        # === WEAKNESSES (метрики < 55%) ===
        for metric_name, score in all_metrics.items():
            if score < 55:
                text = self._get_text_for_metric(metric_name, score, 'weakness', raw_data)
                if text:
                    swot['weaknesses'].append({
                        'metric': metric_name,
                        'score': score,
                        'text': text
                    })
        
        # === OPPORTUNITIES (на основе слабостей) ===
        for weakness in swot['weaknesses']:
            metric_name = weakness['metric']
            opportunity = self._get_opportunity_for_weakness(metric_name, weakness, all_metrics, raw_data)
            if opportunity:
                swot['opportunities'].append(opportunity)
        
        # === THREATS (риски травм) ===
        threats = self._analyze_injury_risks(additional_metrics, tension_data, raw_data)
        swot['threats'].extend(threats)
        
        # Если opportunities пусто, пытаемся найти из всех слабых метрик
        if not swot['opportunities']:
            for weakness in swot['weaknesses']:
                opp = self._get_opportunity_for_weakness(weakness['metric'], weakness, all_metrics, raw_data)
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
        raw_data: Dict[str, Any]
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
        raw_data: Dict[str, Any]
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
        
        # Проверяем условие из шаблона
        if 'condition' in template:
            # Вычисляем условие (например, "hip_score < 70")
            condition = template['condition']
            current_score = weakness['score']
            
            # Подставляем значения в условие
            condition_eval = condition.replace(f'{metric_name}_score', str(current_score))
            # Простая проверка условий
            try:
                if '<' in condition_eval:
                    threshold = float(condition_eval.split('<')[1].strip())
                    if not (current_score < threshold):
                        return None
                elif '>' in condition_eval:
                    threshold = float(condition_eval.split('>')[1].strip())
                    if not (current_score > threshold):
                        return None
            except:
                pass  # Если не удалось проверить, продолжаем
        
        # Рассчитываем значения для подстановки из шаблона
        values = {}
        if 'calculation' in template:
            calc = template['calculation']
            current_score = weakness['score']
            
            for key, formula in calc.items():
                try:
                    # Подставляем значения в формулу
                    formula_eval = formula.replace(f'{metric_name}_score', str(current_score))
                    # Простые вычисления
                    if 'min(' in formula_eval:
                        # min(hip_score + 20, 85)
                        expr = formula_eval.replace('min(', '').replace(')', '')
                        parts = expr.split(',')
                        val1 = eval(parts[0].replace(f'{metric_name}_score', str(current_score)))
                        val2 = float(parts[1].strip())
                        values[key] = int(min(val1, val2))
                    elif '*' in formula_eval or '+' in formula_eval or '-' in formula_eval:
                        # Простые арифметические операции
                        formula_eval = formula_eval.replace(f'{metric_name}_score', str(current_score))
                        values[key] = int(eval(formula_eval))
                    else:
                        values[key] = int(eval(formula_eval.replace(f'{metric_name}_score', str(current_score))))
                except Exception as e:
                    logger.warning(f"Ошибка вычисления {key} для {metric_name}: {e}")
        
        # Дополнительные значения из метрик
        if metric_name == 'leg_activation' or metric_name == 'leg_efficiency':
            values['current'] = int(all_metrics.get('leg_efficiency', 50))
        
        # Если нет расчетов, используем score напрямую
        if not values and 'text' in template:
            values = {'score': int(weakness['score'])}
        
        try:
            text = template['text'].format(**values, **raw_data)
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
            if not isinstance(template, dict) or 'condition' not in template:
                continue
            
            condition = template['condition']
            condition_met = False
            
            # Проверяем условие
            try:
                if 'tension_count >= 3' in condition:
                    # Для плеч и других зон напряжения
                    if tension_data:
                        for side in ['left', 'right']:
                            side_key = f'{side}_shoulder'
                            if side_key in tension_data:
                                tension_count = tension_data[side_key].get('high_tension_count', 0)
                                if tension_count >= 3:
                                    condition_met = True
                                    side_name = template.get('side_map', {}).get(side, side)
                                    text = template['text'].format(
                                        side=side_name,
                                        count=tension_count
                                    )
                                    threats.append({'text': text, 'type': threat_type, 'side': side})
                
                elif 'acute_angle_count >= 5' in condition:
                    # Для локтей
                    if tension_data:
                        for side in ['left', 'right']:
                            side_key = f'{side}_elbow'
                            if side_key in tension_data:
                                angle_count = tension_data[side_key].get('acute_angle_count', 0)
                                if angle_count >= 5:
                                    condition_met = True
                                    side_name = template.get('side_map', {}).get(side, side)
                                    text = template['text'].format(side=side_name)
                                    threats.append({'text': text, 'type': threat_type, 'side': side})
                
                elif 'rotation_count >= 2' in condition:
                    # Для коленей
                    if tension_data:
                        for side in ['left', 'right']:
                            side_key = f'{side}_knee'
                            if side_key in tension_data:
                                rotation_count = tension_data[side_key].get('rotation_count', 0)
                                if rotation_count >= 2:
                                    condition_met = True
                                    side_name = template.get('side_map', {}).get(side, side)
                                    text = template['text'].format(side=side_name, count=rotation_count)
                                    threats.append({'text': text, 'type': threat_type, 'side': side})
                
                elif 'twist_angle >= 30' in condition:
                    # Для поясницы
                    if tension_data and 'lower_back' in tension_data:
                        twist_angle = tension_data['lower_back'].get('twist_angle', 0)
                        if twist_angle >= 30:
                            condition_met = True
                            text = template['text'].format(angle=int(twist_angle))
                            threats.append({'text': text, 'type': threat_type})
                
            except Exception as e:
                logger.warning(f"Ошибка проверки условия для {threat_type}: {e}")
        
        return threats
    
    def estimate_grade(self, technique_metrics: Dict[str, float]) -> str:
        """
        Оценка уровня сложности на основе метрик техники
        
        Returns:
            строка с диапазоном уровня (например, "6a-6b")
        """
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
