# 🔍 CODE REVIEW: ClimbAI BoulderVision

**Дата:** 2026-02-07  
**Ревьюер:** Code Review Expert  
**Область:** Telegram Bot для анализа техники скалолазания

---

## 📊 ИТОГОВАЯ ОЦЕНКА

| Категория | Оценка | Критичность |
|-----------|--------|-------------|
| Безопасность | ⚠️ 6/10 | ВЫСОКАЯ |
| Производительность | ⚠️ 5/10 | ВЫСОКАЯ |
| Архитектура (SOLID) | ✅ 7/10 | СРЕДНЯЯ |
| Обработка ошибок | ⚠️ 5/10 | ВЫСОКАЯ |

---

## 🚨 КРИТИЧНЫЕ ПРОБЛЕМЫ

### 1. **БЕЗОПАСНОСТЬ: Отсутствие валидации входных данных (HIGH RISK)**

**Файл:** `app/bot/handlers.py:174-189`

```python
# УЯЗВИМОСТЬ: cv2.VideoCapture не проверяет корректность видео
cap = cv2.VideoCapture(str(video_path))
if cap.isOpened():
    fps = cap.get(cv2.CAP_PROP_FPS) or 1
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    duration_sec = frames / fps
```

**Проблемы:**
- Нет проверки на битые/поврежденные видеофайлы
- `cv2.VideoCapture` может вернуть некорректные метаданные
- Отсутствует проверка на допустимые форматы видео
- Возможен DoS через специально созданный видеофайл

**Решение:**
```python
import magic  # python-magic для проверки MIME-типа

def validate_video_file(video_path: Path) -> Tuple[bool, str]:
    """Валидация видеофайла перед обработкой"""
    # 1. Проверка MIME-типа
    mime = magic.from_file(str(video_path), mime=True)
    allowed_mimes = ['video/mp4', 'video/quicktime', 'video/x-msvideo']
    if mime not in allowed_mimes:
        return False, f"Недопустимый формат видео: {mime}"
    
    # 2. Проверка на битый файл
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False, "Не удалось открыть видеофайл"
    
    # 3. Попытка прочитать несколько кадров для валидации
    frame_count = 0
    for _ in range(5):
        ret, frame = cap.read()
        if ret:
            frame_count += 1
    
    cap.release()
    
    if frame_count == 0:
        return False, "Видеофайл не содержит читаемых кадров"
    
    return True, "OK"

# В handlers.py:
is_valid, error_msg = validate_video_file(video_path)
if not is_valid:
    await status_msg.edit_text(f"❌ {error_msg}")
    video_path.unlink(missing_ok=True)  # Удаляем битый файл
    return
```

---

### 2. **БЕЗОПАСНОСТЬ: SQL Injection риск через ORM (MEDIUM RISK)**

**Файл:** `app/database/crud.py` (предполагаемо)

**Проблема:** Если где-то используется `.filter()` с конкатенацией строк:
```python
# ПЛОХО:
session.query(User).filter(f"username = '{username}'")
```

**Решение:** ВСЕГДА использовать параметризованные запросы:
```python
# ХОРОШО:
session.query(User).filter(User.username == username)
```

---

### 3. **RACE CONDITION: Параллельная обработка видео (HIGH RISK)**

**Файл:** `app/video/processor.py:116-300`

**Проблема:**
- `VideoProcessor` не thread-safe
- Если один пользователь отправит 2 видео быстро, общие переменные (например, `self.overlays`) могут быть перезаписаны

**Решение:**
```python
class VideoProcessor:
    def __init__(self):
        # Убираем состояние из __init__, создаём для каждого запроса
        pass
    
    async def process_video(self, video_path: Path, ...):
        # Создаём изолированные объекты для каждого запроса
        overlays = VideoOverlays()
        bv_metrics = BoulderVisionMetrics(buffer_size=BOULDERVISION_BUFFER_SIZE)
        tension_analyzer = BodyTensionAnalyzer()
        # ...
```

**Или использовать asyncio.Lock:**
```python
import asyncio

class VideoProcessor:
    def __init__(self):
        self._lock = asyncio.Lock()
        # ...
    
    async def process_video(self, video_path: Path, ...):
        async with self._lock:
            # Обработка
            pass
```

---

### 4. **ПРОИЗВОДИТЕЛЬНОСТЬ: N+1 Query Problem (MEDIUM RISK)**

**Файл:** `app/bot/handlers.py:100-120` (progress_command)

```python
videos = get_user_videos(session, db_user.id, limit=5)

for i, video in enumerate(videos, 1):
    response += f"{i}. Качество: {video.avg_pose_quality:.1f}%"
    if video.fall_detected:
        response += " 🚨"
    response += f"\n   Эксперт: {video.expert_assigned}\n"
    response += f"   Нейротип: {video.neuro_type}\n\n"
```

**Проблема:** Если `expert_assigned` или `neuro_type` — это связи (foreign keys), то для каждого видео будет дополнительный SQL-запрос.

**Решение:**
```python
# В crud.py:
def get_user_videos(session, user_id: int, limit: int = 5):
    return (
        session.query(Video)
        .options(
            joinedload(Video.expert),  # Eager loading
            joinedload(Video.neuro_type_rel)
        )
        .filter(Video.user_id == user_id)
        .order_by(Video.created_at.desc())
        .limit(limit)
        .all()
    )
```

---

### 5. **MEMORY LEAK: Неочищенные ресурсы (HIGH RISK)**

**Файл:** `app/video/processor.py:138-298`

**Проблемы:**
1. `cv2.VideoCapture` и `cv2.VideoWriter` могут не освобождаться при исключении
2. Временные файлы не удаляются при ошибке

**Решение:**
```python
async def process_video(self, video_path: Path, ...):
    cap = None
    out = None
    output_path = None
    
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {video_path}")
        
        # ... обработка ...
        
    except Exception as e:
        logger.error(f"Ошибка обработки видео: {e}", exc_info=True)
        raise
    finally:
        # Освобождаем ресурсы
        if cap:
            cap.release()
        if out:
            out.release()
        
        # Очищаем временные файлы
        if output_path and output_path.exists():
            try:
                output_path.unlink()
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
```

---

### 6. **ОБРАБОТКА ОШИБОК: Пустые except блоки (MEDIUM RISK)**

**Файл:** `app/video/overlays.py:243, 268, 302, 314, 366, 432, 456, 784`

```python
try:
    # ...
except:
    return 50.0  # ПЛОХО: проглатываем все исключения
```

**Проблемы:**
- Невозможно отследить реальные ошибки
- Скрывает баги в коде
- Может маскировать критические проблемы (например, KeyboardInterrupt)

**Решение:**
```python
try:
    # ...
except (AttributeError, ValueError, ZeroDivisionError) as e:
    logger.debug(f"Ошибка расчёта силы: {e}", exc_info=True)
    return 50.0
# НЕ ловим BaseException, SystemExit, KeyboardInterrupt!
```

---

### 7. **ПРОИЗВОДИТЕЛЬНОСТЬ: Избыточное копирование кадров (MEDIUM RISK)**

**Файл:** `app/video/overlays.py:1076, 1369, 1454, 1508`

```python
result = frame.copy()  # Полное копирование кадра в памяти
overlay = result.copy()  # Ещё одно копирование!
cv2.circle(overlay, (cx, cy), radius + 15, (30, 30, 30), -1)
cv2.addWeighted(result, 0.15, overlay, 0.85, 0, result)
```

**Проблема:** Для видео 1920x1080 каждый `frame.copy()` копирует ~6 МБ. При 30 FPS и длительности 2 минуты = **~21 ГБ** копирований в памяти!

**Решение:**
```python
# Вместо копирования всего кадра, используем ROI (Region of Interest)
h, w = frame.shape[:2]
roi_x1, roi_y1 = max(0, cx - radius - 20), max(0, cy - radius - 20)
roi_x2, roi_y2 = min(w, cx + radius + 20), min(h, cy + radius + 20)

# Копируем только нужную область
roi = frame[roi_y1:roi_y2, roi_x1:roi_x2].copy()
overlay_roi = roi.copy()

cv2.circle(overlay_roi, (radius + 20, radius + 20), radius + 15, (30, 30, 30), -1)
cv2.addWeighted(roi, 0.15, overlay_roi, 0.85, 0, roi)

# Записываем обратно
frame[roi_y1:roi_y2, roi_x1:roi_x2] = roi
```

---

### 8. **АРХИТЕКТУРА: Нарушение Single Responsibility Principle (MEDIUM)**

**Файл:** `app/video/processor.py:45-611`

**Проблема:** Класс `VideoProcessor` делает слишком много:
- Обработка видео
- Анализ метрик
- Детекция зацепов
- Генерация отчётов
- Управление базой данных

**Решение:** Разделить на отдельные классы:
```python
# video_pipeline.py
class VideoPipeline:
    def __init__(self):
        self.reader = VideoReader()
        self.pose_detector = PoseDetector()
        self.metrics_analyzer = MetricsAnalyzer()
        self.visualizer = VideoVisualizer()
        self.writer = VideoWriter()
    
    async def process(self, video_path: Path) -> ProcessingResult:
        frames = self.reader.read(video_path)
        for frame in frames:
            landmarks = self.pose_detector.detect(frame)
            metrics = self.metrics_analyzer.analyze(landmarks, frame)
            viz_frame = self.visualizer.draw(frame, metrics)
            self.writer.write(viz_frame)
        
        return ProcessingResult(...)
```

---

### 9. **ПРОИЗВОДИТЕЛЬНОСТЬ: Отсутствие кэширования (LOW RISK)**

**Файл:** `app/video/overlays.py:1462-1474`

```python
# Каждый кадр пересчитываем цвета и категории
categories = ['QF', 'HP', 'DM', 'RR', 'RT', 'DC', 'GR']
colors = [
    (0, 255, 100),   # QF - зелёный
    (100, 200, 255), # HP - голубой
    # ...
]
```

**Решение:**
```python
class VideoOverlays:
    # Константы на уровне класса
    SPIDER_CATEGORIES = ['QF', 'HP', 'DM', 'RR', 'RT', 'DC', 'GR']
    SPIDER_COLORS = [
        (0, 255, 100), (100, 200, 255), (255, 200, 0),
        (200, 100, 255), (255, 150, 0), (0, 200, 255), (255, 100, 100)
    ]
```

---

### 10. **БЕЗОПАСНОСТЬ: Logging чувствительных данных (LOW RISK)**

**Файл:** `app/bot/handlers.py:130, 135`

```python
logger.info(f"📹 Получено видео от пользователя {update.effective_user.id}")
logger.info(f"📹 Обработка видео: file_id={video_file.file_id}, size={video_file.file_size}")
```

**Проблема:** `file_id` может считаться чувствительными данными (PII).

**Решение:**
```python
# Хэшируем или маскируем чувствительные данные
import hashlib

user_id_hash = hashlib.sha256(str(update.effective_user.id).encode()).hexdigest()[:8]
logger.info(f"📹 Получено видео от пользователя {user_id_hash}")
```

---

## ✅ ПОЛОЖИТЕЛЬНЫЕ АСПЕКТЫ

1. **Хорошая структура проекта** — модули логически разделены
2. **Логирование присутствует** — хоть и с недостатками
3. **Использование async/await** — правильная архитектура для Telegram bot
4. **Типизация функций** — Dict[str, Any], Path, Optional используются корректно
5. **Комментарии в коде** — хорошая документация функций

---

## 📋 РЕКОМЕНДАЦИИ ПО ПРИОРИТЕТАМ

### Немедленно (0-1 день):
1. ✅ Добавить валидацию видеофайлов (защита от DoS)
2. ✅ Исправить race condition в VideoProcessor (изоляция состояния)
3. ✅ Добавить `finally` блоки для освобождения ресурсов

### Краткосрочно (1-2 недели):
4. ⚠️ Заменить пустые `except` на конкретные исключения
5. ⚠️ Оптимизировать копирование кадров (использовать ROI)
6. ⚠️ Исправить N+1 query problem

### Среднесрочно (1 месяц):
7. 📊 Рефакторинг VideoProcessor (разделение на классы)
8. 📊 Добавить кэширование констант
9. 📊 Ревью всех SQL-запросов на параметризацию

---

## 🛠️ ИНСТРУМЕНТЫ ДЛЯ МОНИТОРИНГА

**Рекомендуемые инструменты:**

1. **Безопасность:**
   - `bandit` — сканер уязвимостей Python кода
   - `safety` — проверка зависимостей на известные CVE
   ```bash
   pip install bandit safety
   bandit -r app/
   safety check
   ```

2. **Производительность:**
   - `py-spy` — профайлер для Python
   - `memory_profiler` — анализ утечек памяти
   ```bash
   pip install py-spy memory-profiler
   py-spy record -o profile.svg -- python run_bot.py
   ```

3. **Качество кода:**
   - `pylint` — статический анализатор
   - `mypy` — проверка типов
   ```bash
   pip install pylint mypy
   pylint app/
   mypy app/ --ignore-missing-imports
   ```

---

## 📝 ИТОГОВЫЕ МЕТРИКИ

- **Найдено критичных проблем:** 3 (race condition, memory leak, валидация)
- **Найдено средних проблем:** 5 (N+1, исключения, производительность)
- **Найдено низких проблем:** 2 (кэширование, логирование)
- **Оценка готовности к продакшену:** 60%

**Вывод:** Код функционален, но требует доработки перед развертыванием в продакшн. Критичные проблемы должны быть исправлены в первую очередь.
