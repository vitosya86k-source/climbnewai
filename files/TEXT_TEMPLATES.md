# Текстовые шаблоны ClimbAI

**Версия:** 1.0  
**Назначение:** Генерация отчётов без использования ИИ

---

## Принцип работы

Каждая метрика имеет 4 уровня: `excellent` (≥75%), `good` (60-74%), `medium` (45-59%), `poor` (<45%).
Для каждого уровня есть готовый текст с плейсхолдерами для вставки значений.

---

## 1. Базовые метрики техники

### Quiet Feet (Точность ног)

```python
QUIET_FEET_TEMPLATES = {
    "name": "Quiet Feet (Точность ног)",
    "description_short": "Умение ставить ногу сразу в нужное место, без переставления.",
    
    "excellent": {
        "score_text": "Точные ноги — {score}%",
        "detail": "Ставите ногу сразу в нужное место. {repositions} перестановки на зацепку — это уровень {grade}+.",
        "strength": "Точные ноги {score}% — ставите ногу сразу в нужное место, экономите энергию."
    },
    
    "good": {
        "score_text": "Хорошая работа ног — {score}%",
        "detail": "{repositions} перестановки на зацепку — небольшие корректировки, но в целом хорошо.",
        "strength": "Работа ног {score}% — редкие перестановки, это экономит силы."
    },
    
    "medium": {
        "score_text": "Частые перестановки — {score}%",
        "detail": "{repositions} перестановки на зацепку. Норма для вашего уровня — менее {norm}. Есть над чем работать.",
        "weakness": "Перестановки ног {score}% — {repositions} движений на зацепку вместо {norm}. Съедает энергию."
    },
    
    "poor": {
        "score_text": "Ноги «ищут» зацепку — {score}%",
        "detail": "{repositions} перестановки на зацепку — это в {times}x больше нормы. Большие потери энергии.",
        "weakness": "Ноги «ищут» зацепку — {score}%. {repositions} перестановок вместо {norm}. Критично для прогресса."
    },
    
    # Нормы для разных уровней
    "norms": {
        "5a-5c": 4.0,
        "6a-6b": 2.5,
        "6c-7a": 2.0,
        "7b+": 1.5
    }
}
```

### Hip Position (Положение таза)

```python
HIP_POSITION_TEMPLATES = {
    "name": "Hip Position (Положение таза)",
    "description_short": "Близость таза к стене. Чем ближе — тем меньше нагрузка на руки.",
    
    "excellent": {
        "score_text": "Отличное положение таза — {score}%",
        "detail": "Отклонение {angle}° — таз у стены, вес на ногах, руки разгружены.",
        "strength": "Положение таза {score}% — вес на ногах, руки отдыхают. Отличная техника."
    },
    
    "good": {
        "score_text": "Хорошее положение — {score}%",
        "detail": "Отклонение {angle}° — таз достаточно близко к стене.",
        "strength": "Положение таза {score}% — небольшое отклонение, но в целом хорошо."
    },
    
    "medium": {
        "score_text": "Таз отклонён — {score}%",
        "detail": "Отклонение {angle}° — норма менее 15°. Руки перегружаются.",
        "weakness": "Таз отклонён — {score}% ({angle}°). Руки несут лишние {overload}% веса."
    },
    
    "poor": {
        "score_text": "Таз далеко от стены — {score}%",
        "detail": "Отклонение {angle}° — вы «висите на руках». Быстрое истощение неизбежно.",
        "weakness": "Таз далеко от стены — {score}% ({angle}°). Руки перегружены на {overload}%. Главная точка роста."
    },
    
    "opportunity": "Если улучшить положение таза до {target}% — руки будут уставать на {reduction}% меньше."
}
```

### Противовес (Diagonal Movement)

```python
DIAGONAL_TEMPLATES = {
    "name": "Противовес (Диагональ)",
    "description_short": "Координация «правая рука — левая нога» и наоборот. Основа баланса.",
    
    "excellent": {
        "score_text": "Противовес — {score}%",
        "detail": "Отличная диагональная координация. Движения сбалансированы, это уровень {grade}+.",
        "strength": "Противовес {score}% — отличная диагональная работа, баланс стабильный."
    },
    
    "good": {
        "score_text": "Диагональ работает — {score}%",
        "detail": "Хорошая координация противоположных конечностей. Есть небольшие сбои.",
        "strength": "Противовес {score}% — диагональ работает, баланс хороший."
    },
    
    "medium": {
        "score_text": "Диагональ слабая — {score}%",
        "detail": "Часто двигаетесь «квадратом» — обе руки, потом обе ноги. Теряете баланс.",
        "weakness": "Противовес {score}% — движения «квадратом», тело раскачивается."
    },
    
    "poor": {
        "score_text": "Нет диагонали — {score}%",
        "detail": "Координация хаотичная. Тело постоянно раскачивается, много энергии уходит на стабилизацию.",
        "weakness": "Нет диагонали — {score}%. Хаотичные движения, много энергии на стабилизацию."
    }
}
```

### Считывание (Route Reading)

```python
ROUTE_READING_TEMPLATES = {
    "name": "Считывание (Планирование)",
    "description_short": "Паузы для просмотра маршрута — до старта и в процессе лазания.",
    
    "excellent": {
        "score_text": "Считывание — {score}%",
        "detail": "{start_time} сек до старта + {pauses} паузы для просмотра. Продуманное лазание.",
        "strength": "Считывание {score}% — планируете маршрут, делаете паузы. Признак опытного скалолаза."
    },
    
    "good": {
        "score_text": "Есть планирование — {score}%",
        "detail": "{start_time} сек до старта + {pauses} паузы. Не лезете вслепую.",
        "strength": "Считывание {score}% — есть планирование, не лезете вслепую."
    },
    
    "medium": {
        "score_text": "Мало планирования — {score}%",
        "detail": "{start_time} сек до старта, редкие паузы. Импульсивное лазание.",
        "weakness": "Считывание {score}% — мало пауз для просмотра. Добавьте планирование."
    },
    
    "poor": {
        "score_text": "Импульсивное лазание — {score}%",
        "detail": "Сразу бросаетесь на маршрут без плана. Много ошибок и срывов.",
        "weakness": "Импульсивное лазание — {score}%. Бросаетесь на маршрут без плана."
    }
}
```

### Ритм (Movement Rhythm)

```python
RHYTHM_TEMPLATES = {
    "name": "Ритм (Равномерность)",
    "description_short": "Стабильность темпа движений — без резких ускорений и замедлений.",
    
    "excellent": {
        "score_text": "Ритм — {score}%",
        "detail": "Разброс темпа ±{variance}мс — как метроном. Полный контроль.",
        "strength": "Ритм {score}% — движения равномерные, полный контроль."
    },
    
    "good": {
        "score_text": "Стабильный темп — {score}%",
        "detail": "Разброс ±{variance}мс — небольшие колебания, но в целом ровно.",
        "strength": "Ритм {score}% — темп стабильный, небольшие колебания."
    },
    
    "medium": {
        "score_text": "Нестабильный темп — {score}%",
        "detail": "Разброс ±{variance}мс — ритм сбивается на сложных участках.",
        "weakness": "Ритм {score}% — темп сбивается на сложных участках. Разброс ±{variance}мс."
    },
    
    "poor": {
        "score_text": "Рваный ритм — {score}%",
        "detail": "Разброс ±{variance}мс — хаотичные ускорения и замедления. Признак стресса.",
        "weakness": "Рваный ритм — {score}%. Разброс ±{variance}мс. Признак стресса или паники."
    },
    
    "opportunity": "Ровный ритм снизит расход энергии на {saved}% и уберёт панику на сложных участках."
}
```

### Контроль динамики (Dynamic Control)

```python
DYNAMIC_CONTROL_TEMPLATES = {
    "name": "Контроль динамики",
    "description_short": "Качество после бросков — точность приземления и скорость стабилизации.",
    
    "excellent": {
        "score_text": "Контроль динамики — {score}%",
        "detail": "Стабилизация за {time}с после броска — мгновенный контроль.",
        "strength": "Контроль динамики {score}% — после бросков сразу стабилизируетесь."
    },
    
    "good": {
        "score_text": "Хороший контроль — {score}%",
        "detail": "Стабилизация за {time}с — быстро восстанавливаете баланс.",
        "strength": "Контроль динамики {score}% — динамические ходы под контролем."
    },
    
    "medium": {
        "score_text": "Долгая стабилизация — {score}%",
        "detail": "Стабилизация за {time}с — долго «ловите» баланс после броска.",
        "weakness": "Контроль динамики {score}% — после бросков долго «ловите» баланс ({time}с)."
    },
    
    "poor": {
        "score_text": "Теряете контроль — {score}%",
        "detail": "Стабилизация за {time}с (норма <0.5с) — близко к срыву после каждого броска.",
        "weakness": "Теряете контроль после бросков — {score}%. Стабилизация {time}с вместо 0.5с."
    }
}
```

### Grip Release (Перехваты)

```python
GRIP_RELEASE_TEMPLATES = {
    "name": "Grip Release (Перехваты)",
    "description_short": "Плавность отпускания зацепов — без рывков и резких движений.",
    
    "excellent": {
        "score_text": "Мягкие перехваты — {score}%",
        "detail": "Отпускаете зацепы плавно, без рывков. Текучие движения.",
        "strength": "Перехваты {score}% — плавные, мягкие движения. Экономия энергии."
    },
    
    "good": {
        "score_text": "Хорошие перехваты — {score}%",
        "detail": "Достаточно плавные движения, редкие рывки.",
        "strength": "Перехваты {score}% — достаточно плавные движения рук."
    },
    
    "medium": {
        "score_text": "Есть рывки — {score}%",
        "detail": "Заметные рывки при отпускании. Теряете баланс.",
        "weakness": "Перехваты {score}% — рывки при отпускании, теряете баланс."
    },
    
    "poor": {
        "score_text": "Резкие перехваты — {score}%",
        "detail": "Дёргаете зацепы, резкие движения. Большие потери энергии и баланса.",
        "weakness": "Резкие перехваты — {score}%. Дёргаете зацепы, теряете баланс и энергию."
    },
    
    "opportunity": "Плавные перехваты — это +1 категория сложности. Сейчас это ваш потолок."
}
```

---

## 2. Дополнительные метрики

### Стабильность

```python
STABILITY_TEMPLATES = {
    "name": "Стабильность",
    "description_short": "Контроль положения тела — без дрожания и лишних микрокоррекций.",
    
    "excellent": {
        "value_text": "{score}%",
        "hint": "контроль тела",
        "detail": "Тело не «гуляет», отличный контроль центра масс.",
        "strength": "Стабильность {score}% — тело не «гуляет», минимум лишних движений."
    },
    
    "good": {
        "value_text": "{score}%",
        "hint": "контроль тела",
        "detail": "Хороший контроль положения тела, небольшие колебания.",
        "strength": "Стабильность {score}% — хороший контроль положения."
    },
    
    "medium": {
        "value_text": "{score}%",
        "hint": "контроль тела",
        "detail": "Заметное дрожание, тело «ищет» баланс.",
        "weakness": "Стабильность {score}% — тело «гуляет», много микрокоррекций."
    },
    
    "poor": {
        "value_text": "{score}%",
        "hint": "контроль тела",
        "detail": "Сильная нестабильность, много энергии уходит на удержание равновесия.",
        "weakness": "Стабильность {score}% — много энергии на удержание равновесия."
    }
}
```

### Истощение

```python
EXHAUSTION_TEMPLATES = {
    "name": "Истощение",
    "description_short": "Накопленная усталость — как меняется качество к концу маршрута.",
    
    "low": {  # < 30%
        "value_text": "{score}%",
        "hint": "усталость к финишу",
        "detail": "Минимальное истощение, резерв сил есть.",
        "strength": "Истощение всего {score}% — хороший резерв сил, можно брать длиннее."
    },
    
    "moderate": {  # 30-50%
        "value_text": "{score}%",
        "hint": "усталость к финишу",
        "detail": "Умеренное истощение, нормально для сложного маршрута."
    },
    
    "high": {  # 50-70%
        "value_text": "{score}%",
        "hint": "усталость к финишу",
        "detail": "Заметное падение качества к финишу.",
        "weakness": "Истощение {score}% — падение качества к финишу.",
        "threat": "Истощение {score}% — последняя часть маршрута в жёлтой зоне."
    },
    
    "critical": {  # > 70%
        "value_text": "{score}%",
        "hint": "усталость к финишу",
        "detail": "Сильное истощение, последняя часть маршрута в красной зоне.",
        "threat": "Истощение {score}% — к финишу падение контроля на {drop}%. Риск срыва."
    }
}
```

### Эффективность рук

```python
ARM_EFFICIENCY_TEMPLATES = {
    "name": "Руки",
    "description_short": "Какой процент веса несут руки. Норма: 30-40%.",
    
    "optimal": {  # 30-40%
        "value_text": "{arm_load}%",
        "hint": "% нагрузки",
        "detail": "Идеальное распределение — ноги работают, руки направляют.",
        "strength": "Руки несут {arm_load}% — идеально, ноги работают."
    },
    
    "acceptable": {  # 40-50%
        "value_text": "{arm_load}%",
        "hint": "% нагрузки",
        "detail": "Чуть больше нормы, но в целом хорошо."
    },
    
    "overloaded": {  # 50-65%
        "value_text": "{arm_load}%",
        "hint": "% нагрузки",
        "detail": "Руки перегружены, быстрое истощение.",
        "weakness": "Руки перегружены — {arm_load}% вместо 30-40%. Переносите вес на ноги."
    },
    
    "critical": {  # > 65%
        "value_text": "{arm_load}%",
        "hint": "% нагрузки",
        "detail": "Критический перегруз рук. Висите на руках.",
        "weakness": "Руки {arm_load}% — критический перегруз. Техника требует работы."
    }
}
```

### Эффективность ног

```python
LEG_EFFICIENCY_TEMPLATES = {
    "name": "Ноги",
    "description_short": "Какой процент веса несут ноги. Норма: 60-70%.",
    
    "optimal": {  # 60-70%
        "value_text": "{leg_load}%",
        "hint": "% нагрузки",
        "detail": "Отлично — ноги ваш двигатель.",
        "strength": "Ноги несут {leg_load}% — отлично, это ваш двигатель."
    },
    
    "good": {  # 50-60%
        "value_text": "{leg_load}%",
        "hint": "% нагрузки",
        "detail": "Хорошо, но можно активнее использовать ноги.",
        "opportunity": "Ноги несут {leg_load}%. Если довести до 65% — откроются нависания."
    },
    
    "underused": {  # 40-50%
        "value_text": "{leg_load}%",
        "hint": "% нагрузки",
        "detail": "Ноги недогружены, упущенный потенциал.",
        "weakness": "Ноги только {leg_load}% — недогружены. Активнее толкайтесь."
    },
    
    "passive": {  # < 40%
        "value_text": "{leg_load}%",
        "hint": "% нагрузки",
        "detail": "Ноги почти не работают. Критично для прогресса.",
        "weakness": "Ноги {leg_load}% — почти не работают. Главная точка роста."
    }
}
```

### Восстановление

```python
RECOVERY_TEMPLATES = {
    "name": "Восстановление",
    "description_short": "Умение находить позы для отдыха и восстанавливаться на маршруте.",
    
    "excellent": {
        "value_text": "{score}%",
        "hint": "качество отдыха",
        "detail": "Отлично умеете восстанавливаться, находите хорошие позиции.",
        "strength": "Восстановление {score}% — умеете находить позы для отдыха и вытряхивать руки."
    },
    
    "good": {
        "value_text": "{score}%",
        "hint": "качество отдыха",
        "detail": "Делаете паузы, даёте рукам отдых.",
        "strength": "Восстановление {score}% — делаете паузы, даёте рукам отдых."
    },
    
    "medium": {
        "value_text": "{score}%",
        "hint": "качество отдыха",
        "detail": "Редко отдыхаете или отдых неэффективен.",
        "weakness": "Восстановление {score}% — редкие паузы или отдых неэффективен."
    },
    
    "poor": {
        "value_text": "{score}%",
        "hint": "качество отдыха",
        "detail": "Не умеете восстанавливаться, лезете на износ.",
        "weakness": "Не отдыхаете — {score}%. Лезете на износ без пауз."
    },
    
    "opportunity": "Научитесь отдыхать на маршруте — сможете лезть длиннее на {time_gain} минут."
}
```

---

## 3. Угрозы (Threats) — шаблоны для рисков травм

```python
THREAT_TEMPLATES = {
    "shoulder": {
        "condition": "tension_count >= 3",  # зажим в 3+ точках
        "text": "{side} плечо — зажим в {count} точках маршрута. Риск импинджмента при сохранении паттерна.",
        "side_map": {"left": "Левое", "right": "Правое"}
    },
    
    "elbow": {
        "condition": "acute_angle_count >= 5",  # острый угол 5+ раз
        "text": "{side} локоть — частые углы <70° под нагрузкой. Риск эпикондилита («локоть скалолаза»).",
        "side_map": {"left": "Левый", "right": "Правый"}
    },
    
    "knee_rotation": {
        "condition": "rotation_count >= 2",  # ротация под нагрузкой 2+ раза
        "text": "{side} колено — ротация под нагрузкой {count} раз за пролаз. Риск повреждения мениска.",
        "side_map": {"left": "Левое", "right": "Правое"}
    },
    
    "lower_back": {
        "condition": "twist_angle >= 30",  # скручивание 30°+
        "text": "Поясница — скручивание {angle}° под нагрузкой. Риск протрузии при хроническом паттерне."
    },
    
    "exhaustion_critical": {
        "condition": "exhaustion >= 70",
        "text": "Истощение {percent}% — последняя часть маршрута в красной зоне. Падение контроля = риск срыва."
    },
    
    "overtraining": {
        "condition": "multiple_signs",  # несколько признаков
        "text": "Паттерн указывает на перетренированность: рекомендован отдых или снижение нагрузки."
    }
}
```

---

## 4. Возможности (Opportunities) — шаблоны

```python
OPPORTUNITY_TEMPLATES = {
    "hip_position": {
        "condition": "hip_score < 70",
        "text": "Если улучшить положение таза до {target}% — руки будут уставать на {reduction}% меньше.",
        "calculation": {
            "target": "min(hip_score + 20, 85)",
            "reduction": "(target - hip_score) * 1.5"
        }
    },
    
    "quiet_feet": {
        "condition": "quiet_feet_score < 70",
        "text": "Работа над точностью ног уберёт {saved} лишних движений за маршрут — экономия {energy}% энергии.",
        "calculation": {
            "saved": "(current_repositions - target_repositions) * hold_count",
            "energy": "saved * 2"
        }
    },
    
    "grip_release": {
        "condition": "grip_score < 60",
        "text": "Плавные перехваты — это +1 категория сложности. Сейчас это ваш потолок."
    },
    
    "leg_activation": {
        "condition": "leg_load < 60",
        "text": "Ноги несут только {current}% веса. Если довести до 65% — откроются нависания."
    },
    
    "rhythm": {
        "condition": "rhythm_score < 65",
        "text": "Ровный ритм снизит расход энергии на {saved}% и уберёт панику на сложных участках.",
        "calculation": {
            "saved": "(70 - rhythm_score) * 0.5"
        }
    },
    
    "recovery": {
        "condition": "recovery_score < 60 AND exhaustion > 50",
        "text": "Научитесь отдыхать на маршруте — сможете лезть длиннее на {time}% времени.",
        "calculation": {
            "time": "(70 - recovery_score) * 0.8"
        }
    }
}
```

---

## 5. Оценка уровня сложности

```python
GRADE_ESTIMATION = {
    "weights": {
        "quiet_feet": 0.20,
        "hip_position": 0.20,
        "diagonal": 0.15,
        "grip_release": 0.15,
        "rhythm": 0.10,
        "dynamic_control": 0.10,
        "route_reading": 0.10
    },
    
    "grade_table": [
        {"min_score": 90, "grade": "7b+", "text": "Техника соответствует уровню 7b+"},
        {"min_score": 85, "grade": "7a—7b", "text": "Техника соответствует уровню 7a—7b"},
        {"min_score": 80, "grade": "6c—7a", "text": "Техника соответствует уровню 6c—7a"},
        {"min_score": 75, "grade": "6b—6c", "text": "Техника соответствует уровню 6b—6c"},
        {"min_score": 70, "grade": "6a—6b", "text": "Техника соответствует уровню 6a—6b"},
        {"min_score": 65, "grade": "5c—6a", "text": "Техника соответствует уровню 5c—6a"},
        {"min_score": 60, "grade": "5b—5c", "text": "Техника соответствует уровню 5b—5c"},
        {"min_score": 50, "grade": "5a—5b", "text": "Техника соответствует уровню 5a—5b"},
        {"min_score": 0, "grade": "до 5a", "text": "Техника соответствует уровню до 5a"}
    ],
    
    "potential_text": "Потенциал при коррекции слабых мест: {potential_grade}"
}
```

---

## 6. Алгоритм выбора текста

```python
def get_text_for_metric(metric_name, score, raw_data):
    """
    Выбор текста для метрики на основе балла.
    
    metric_name: название метрики
    score: балл 0-100
    raw_data: сырые данные для подстановки
    
    Возвращает: словарь с текстами
    """
    templates = METRIC_TEMPLATES[metric_name]
    
    # Определяем уровень
    if score >= 75:
        level = "excellent"
    elif score >= 60:
        level = "good"
    elif score >= 45:
        level = "medium"
    else:
        level = "poor"
    
    # Получаем шаблоны для уровня
    level_templates = templates.get(level, {})
    
    # Подставляем значения
    result = {}
    for key, template in level_templates.items():
        result[key] = template.format(
            score=score,
            **raw_data
        )
    
    return result


def generate_swot(all_metrics):
    """
    Генерация SWOT на основе всех метрик.
    """
    swot = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }
    
    # Strengths: метрики >= 75%
    for name, data in all_metrics.items():
        if data["score"] >= 75:
            text = get_text_for_metric(name, data["score"], data["raw"])
            if "strength" in text:
                swot["strengths"].append({
                    "metric": name,
                    "score": data["score"],
                    "text": text["strength"]
                })
    
    # Weaknesses: метрики < 55%
    for name, data in all_metrics.items():
        if data["score"] < 55:
            text = get_text_for_metric(name, data["score"], data["raw"])
            if "weakness" in text:
                swot["weaknesses"].append({
                    "metric": name,
                    "score": data["score"],
                    "text": text["weakness"]
                })
    
    # Opportunities: на основе слабостей
    for weakness in swot["weaknesses"]:
        opp_template = OPPORTUNITY_TEMPLATES.get(weakness["metric"])
        if opp_template:
            # Рассчитываем значения для подстановки
            values = calculate_opportunity_values(weakness, all_metrics)
            swot["opportunities"].append({
                "text": opp_template["text"].format(**values)
            })
    
    # Threats: на основе зон напряжения и истощения
    threats = check_injury_risks(all_metrics)
    swot["threats"].extend(threats)
    
    # Ограничиваем количество
    swot["strengths"] = swot["strengths"][:4]
    swot["weaknesses"] = swot["weaknesses"][:4]
    swot["opportunities"] = swot["opportunities"][:3]
    swot["threats"] = swot["threats"][:3]
    
    return swot
```

---

## 7. Методологическая справка

```python
METHODOLOGY_NOTE = """
Метрики основаны на признанных методологиях обучения скалолазанию:

• Eric J. Hörst «Training for Climbing» — принципы экономичности движений, 
  quiet feet, hip position, энергосбережение

• John Kettle «Coaching Climbing» — техника наблюдения и анализа движений

• Dan Hague & Douglas Hunter «Self-Coached Climber» — диагональное движение, 
  противовес, считывание маршрута

• Movement for Climbers — анализ паттернов движения, ритм, динамика

Если хотите углубиться в методологию — рекомендуем книгу 
Eric J. Hörst «Training for Climbing», глава о технике.
"""
```

---

**Конец документа с шаблонами**
