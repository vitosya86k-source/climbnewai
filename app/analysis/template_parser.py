"""
Парсер шаблонов из TEXT_TEMPLATES.md

Полноценный парсер для загрузки шаблонов из Markdown файла
"""

import re
import ast
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TemplateParser:
    """Парсер шаблонов из TEXT_TEMPLATES.md"""
    
    def __init__(self, template_path: Optional[Path] = None):
        """
        Args:
            template_path: путь к файлу TEXT_TEMPLATES.md
        """
        if template_path is None:
            template_path = Path(__file__).parent.parent.parent / "files" / "TEXT_TEMPLATES.md"
        self.template_path = Path(template_path)
        self.templates: Dict[str, Dict] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Загрузка и парсинг шаблонов из Markdown файла"""
        if not self.template_path.exists():
            logger.warning(f"⚠️ Файл шаблонов не найден: {self.template_path}")
            self._load_defaults()
            return
        
        try:
            content = self.template_path.read_text(encoding='utf-8')
            
            # Парсим Python-словари из Markdown
            self._parse_metric_templates(content)
            self._parse_swot_templates(content)
            self._parse_grade_estimation(content)
            
            logger.info(f"✅ Загружено шаблонов из {self.template_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки шаблонов: {e}", exc_info=True)
            self._load_defaults()
    
    def _parse_metric_templates(self, content: str):
        """Извлечение шаблонов метрик"""
        # Паттерн для поиска блоков кода с шаблонами метрик
        pattern = r'```python\s*(\w+_TEMPLATES)\s*=\s*\{([^`]+)\}'
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            name = match.group(1)
            body = match.group(2)
            
            try:
                # Очищаем комментарии
                body_clean = re.sub(r'#.*$', '', body, flags=re.MULTILINE)
                
                # Пытаемся распарсить как Python dict
                template_dict = self._safe_eval_dict('{' + body_clean + '}')
                metric_name = name.replace('_TEMPLATES', '').lower()
                self.templates[metric_name] = template_dict
                logger.debug(f"Загружен шаблон для {metric_name}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка парсинга {name}: {e}")
    
    def _safe_eval_dict(self, dict_str: str) -> Dict:
        """Безопасный парсинг строки словаря"""
        # Удаляем комментарии
        dict_str = re.sub(r'#.*$', '', dict_str, flags=re.MULTILINE)
        
        # Удаляем лишние пробелы
        dict_str = re.sub(r'\s+', ' ', dict_str)
        
        # Используем ast.literal_eval для безопасности
        try:
            return ast.literal_eval(dict_str)
        except (ValueError, SyntaxError):
            # Fallback: простой парсинг ключ-значение
            return self._manual_parse(dict_str)
    
    def _manual_parse(self, dict_str: str) -> Dict:
        """Ручной парсинг если ast не справился"""
        result = {}
        
        # Ищем паттерны "key": "value" или "key": {nested}
        # Упрощенная версия - ищем строковые значения
        key_pattern = r'"(\w+)":\s*"([^"]*)"'
        for match in re.finditer(key_pattern, dict_str):
            result[match.group(1)] = match.group(2)
        
        return result
    
    def _parse_swot_templates(self, content: str):
        """Извлечение SWOT шаблонов"""
        # Ищем THREAT_TEMPLATES и OPPORTUNITY_TEMPLATES
        for template_name in ['THREAT_TEMPLATES', 'OPPORTUNITY_TEMPLATES']:
            pattern = rf'```python\s*{template_name}\s*=\s*\{{([^`]+)\}}'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    body = match.group(1)
                    body_clean = re.sub(r'#.*$', '', body, flags=re.MULTILINE)
                    template_dict = self._safe_eval_dict('{' + body_clean + '}')
                    # Сохраняем под обоими ключами для совместимости
                    key_lower = template_name.lower()
                    self.templates[key_lower] = template_dict
                    # Также сохраняем как opportunity_templates/threat_templates
                    if 'OPPORTUNITY' in template_name:
                        self.templates['opportunity_templates'] = template_dict
                    elif 'THREAT' in template_name:
                        self.templates['threat_templates'] = template_dict
                    logger.debug(f"Загружен шаблон {template_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка парсинга {template_name}: {e}")
    
    def _parse_grade_estimation(self, content: str):
        """Извлечение таблицы оценки уровня"""
        pattern = r'```python\s*GRADE_ESTIMATION\s*=\s*\{([^`]+)\}'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                body = match.group(1)
                body_clean = re.sub(r'#.*$', '', body, flags=re.MULTILINE)
                self.templates['grade_estimation'] = self._safe_eval_dict('{' + body_clean + '}')
                logger.debug("Загружена таблица оценки уровня")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка парсинга GRADE_ESTIMATION: {e}")
    
    def _load_defaults(self):
        """Загрузка дефолтных шаблонов (fallback)"""
        # Дефолтные шаблоны остаются в swot_generator.py
        logger.info("Используются дефолтные шаблоны")
    
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
                    logger.warning(f"Отсутствует ключ {e} в raw_data для {metric_name}")
                    result[key] = text  # Возвращаем без подстановки если ключ не найден
        
        return result
