"""
Главный процессор видео с MediaPipe + BoulderVision

Интеграция:
- MediaPipe Pose для детекции скелета
- BoulderVision метрики (Velocity Ratio, Cumulative Distance)
- Roboflow для детекции зацепов (опционально)
- 8 типов визуализации
"""

import cv2
import mediapipe as mp
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import math

from app.config import (
    MEDIAPIPE_MODEL_COMPLEXITY, 
    FRAME_SKIP, 
    TEMP_DIR,
    ROBOFLOW_API_KEY,
    ROBOFLOW_PROJECT,
    ROBOFLOW_MODEL_VERSION,
    BOULDERVISION_BUFFER_SIZE,
    ENABLE_HOLD_DETECTION
)
from app.analysis import (
    FrameAnalyzer,
    FallDetector,
    generate_csv_report,
    BodyTensionAnalyzer,
    InjuryPredictor,
    ClimberNineBoxModel,
    RouteAssessor
)
from app.analysis.csv_generator import analyze_technical_issues
from app.bouldervision import BoulderVisionMetrics, HoldsDetector
from .overlays import VideoOverlays

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Обработчик видео с MediaPipe + BoulderVision
    
    Поддерживает 8 типов визуализации:
    
    Базовые (5):
    - skeleton: скелет с соединениями
    - points: ключевые точки
    - stress: точки напряжения (по углам суставов)
    - center: центр масс и траектория
    - metrics: метрики на видео
    
    BoulderVision (3):
    - heatmap: тепловая карта позиций
    - trajectory: полная траектория движения
    - holds: зацепы + скелет + связи
    
    ВАЖНО: Все объекты с состоянием создаются ВНУТРИ process_video()
    для изоляции между запросами (защита от race condition)
    """
    
    def __init__(self):
        """Инициализация только MediaPipe Pose (без состояния)"""
        self.mp_pose = mp.solutions.pose
        logger.info("✅ VideoProcessor инициализирован (stateless)")
    
    async def process_video(
        self,
        video_path: Path,
        output_overlay: str = "skeleton",
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Обрабатывает видео и возвращает анализ
        
        Args:
            video_path: путь к видео
            output_overlay: тип визуализации (8 вариантов)
            progress_callback: функция для обновления прогресса
            
        Returns:
            dict с результатами анализа включая BoulderVision метрики
        """
        # ИЗОЛЯЦИЯ СОСТОЯНИЯ: создаём объекты для каждого запроса
        # Это защищает от race condition при параллельной обработке
        pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=MEDIAPIPE_MODEL_COMPLEXITY,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        frame_analyzer = FrameAnalyzer()
        fall_detector = FallDetector()
        overlays = VideoOverlays()
        bv_metrics = BoulderVisionMetrics(buffer_size=BOULDERVISION_BUFFER_SIZE)
        tension_analyzer = BodyTensionAnalyzer()
        injury_predictor = InjuryPredictor()
        nine_box_model = ClimberNineBoxModel()
        route_assessor = RouteAssessor()
        
        # Импортируем анализаторы
        from app.analysis.technique_metrics import TechniqueMetricsAnalyzer
        from app.analysis.additional_metrics import AdditionalMetricsAnalyzer
        from app.analysis.swot_generator import SWOTGenerator
        
        technique_analyzer = TechniqueMetricsAnalyzer()
        additional_analyzer = AdditionalMetricsAnalyzer()
        swot_generator = SWOTGenerator()
        
        # Детектор зацепов (опционально)
        holds_detector: Optional[HoldsDetector] = None
        if ENABLE_HOLD_DETECTION and ROBOFLOW_API_KEY and output_overlay == "holds":
            try:
                holds_detector = HoldsDetector(
                    api_key=ROBOFLOW_API_KEY,
                    project_name=ROBOFLOW_PROJECT,
                    model_version=ROBOFLOW_MODEL_VERSION
                )
                logger.info("✅ HoldsDetector создан для этого запроса")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось создать HoldsDetector: {e}")
                holds_detector = None
        
        cap = None
        out = None
        output_path = None
        
        try:
            logger.info(f"🎬 Начало обработки видео: {video_path}")
            logger.info(f"📊 Тип визуализации: {output_overlay}")
            
            # Открываем видео
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                raise ValueError(f"Не удалось открыть видео: {video_path}")
            
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"📹 Видео: {width}x{height}, {fps} FPS, {total_frames} кадров, {duration:.1f}с")
            
            # Подготовка выходного видео
            output_path = TEMP_DIR / f"processed_{video_path.stem}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            
            frame_number = 0
            processed_count = 0
            
            # Для детекции зацепов (кэшируем на первом кадре)
            detected_holds: List = []
            holds_detection_interval = 30  # Детектируем зацепы каждые N кадров
            
            # Сброс состояния анализаторов (локальные объекты, но на всякий случай)
            bv_metrics.reset()
            tension_analyzer.reset()
            if holds_detector:
                holds_detector.reset()
            overlays.reset()
            
            # Обработка кадров
            while cap.isOpened():
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                timestamp = frame_number / fps if fps > 0 else 0
                
                # Пропускаем кадры если нужно
                if frame_number % FRAME_SKIP == 0:
                    # Конвертируем в RGB для MediaPipe
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Детекция позы
                    results = pose.process(frame_rgb)
                    
                    # Базовый анализ кадра
                    frame_data = frame_analyzer.analyze_frame(
                        frame_number,
                        results.pose_landmarks,
                        timestamp
                    )
                    
                    # BoulderVision: анализ метрик движения
                    bv_frame_metrics = bv_metrics.process_frame(
                        results.pose_landmarks,
                        frame_number,
                        timestamp
                    )
                    
                    # Добавляем BV метрики в frame_data
                    frame_data.update({
                        'velocity_ratio': bv_frame_metrics.get('velocity_ratio', 1.0),
                        'cumulative_distance': bv_frame_metrics.get('cumulative_distance', 0.0),
                        'current_velocity': bv_frame_metrics.get('current_velocity', 0.0)
                    })
                    
                    # Детекция зацепов (если включено и это нужный overlay)
                    if holds_detector and output_overlay == "holds":
                        if frame_number % holds_detection_interval == 0:
                            detected_holds = holds_detector.detect_holds(
                                frame, frame_number
                            )
                        
                        # Обновляем взаимодействия с зацепами
                        if detected_holds:
                            holds_detector.update_interactions(
                                results.pose_landmarks,
                                detected_holds,
                                frame_number
                            )
                    
                    # Проверка на падение
                    fall_info = fall_detector.check_fall(
                        frame_data,
                        frame_analyzer.frame_data
                    )

                    # Анализ напряжения (каждый кадр)
                    if results.pose_landmarks:
                        tension_analyzer.analyze_frame(
                            results.pose_landmarks,
                            frame_number
                        )
                        
                        # НОВЫЕ МЕТРИКИ: 7 базовых метрик техники и дополнительные метрики
                        timestamp = frame_number / fps if fps > 0 else frame_number * 0.033
                        
                        # Анализ техники (7 базовых метрик)
                        technique_metrics = technique_analyzer.analyze_frame(
                            results.pose_landmarks,
                            frame_number,
                            timestamp,
                            frame_data
                        )
                        overlays.technique_metrics_history.append(technique_metrics)
                        if len(overlays.technique_metrics_history) > 90:
                            overlays.technique_metrics_history.pop(0)
                        
                        # Дополнительные метрики
                        additional_metrics = additional_analyzer.analyze_frame(
                            results.pose_landmarks,
                            frame_number,
                            frame_data,
                            technique_metrics
                        )
                        overlays.additional_metrics_history.append(additional_metrics)
                        if len(overlays.additional_metrics_history) > 90:
                            overlays.additional_metrics_history.pop(0)
                        
                        # Обновляем overlays с новыми метриками для визуализации
                        if overlays.technique_metrics_history:
                            # Передаём последние метрики в overlays для паутинки
                            latest_technique = overlays.technique_metrics_history[-1]
                            # Обновляем metrics_history для обратной совместимости
                            overlays.metrics_history.append(latest_technique)
                            if len(overlays.metrics_history) > 90:
                                overlays.metrics_history.pop(0)

                    # Отрисовка выбранного типа визуализации
                    if results.pose_landmarks:
                        frame = overlays.apply_overlay(
                            frame,
                            results.pose_landmarks,
                            output_overlay,
                            frame_data,
                            holds_detector=holds_detector,
                            holds=detected_holds if output_overlay == "holds" else None
                        )
                    else:
                        # Если landmarks нет, все равно обновляем историю с None
                        # чтобы метрики не терялись
                        overlays._update_history(None, frame.shape[:2], frame_data)
                    
                    processed_count += 1
                
                # Записываем кадр
                out.write(frame)
                
                # Прогресс
                if progress_callback and frame_number % 30 == 0:
                    progress = int((frame_number / total_frames) * 100)
                    await progress_callback(progress, f"Обработка кадра {frame_number}/{total_frames}")
                
                frame_number += 1
            
            # Закрываем
            cap.release()
            out.release()
            
            logger.info(f"✅ Обработано {processed_count} кадров из {total_frames}")
            
            # Базовая статистика
            statistics = frame_analyzer.get_statistics()
            best_worst = frame_analyzer.find_best_worst_frames()
            technical_issues = analyze_technical_issues(frame_analyzer.frame_data)
            
            # BoulderVision статистика
            bv_summary = bv_metrics.get_summary()
            
            # Статистика зацепов
            holds_analysis = {}
            if holds_detector:
                holds_analysis = holds_detector.get_hold_analysis(fps)
            
            # Генерация CSV
            csv_path = TEMP_DIR / f"analysis_{video_path.stem}.csv"
            generate_csv_report(frame_analyzer.frame_data, csv_path)

            # ========== НОВЫЕ АЛГОРИТМИЧЕСКИЕ АНАЛИЗЫ ==========

            # 1. Анализ напряжения (tension)
            logger.info("Анализ напряжения...")
            tension_summary = tension_analyzer.get_summary()

            # Подготовка video_analysis для других модулей
            video_analysis_temp = {
                'duration': duration,
                'fps': fps,
                'total_frames': total_frames,
                'avg_pose_quality': statistics.get('avg_pose_quality', 0),
                'avg_motion_intensity': statistics.get('avg_motion_intensity', 0),
                'avg_balance_score': statistics.get('avg_balance_score', 0),
                'fall_detected': fall_detector.fall_detected,
                'bouldervision': bv_summary,
                'tension_analysis': tension_summary
            }

            # 2. Прогноз травм
            logger.info("Прогноз травм...")
            injury_predictions = injury_predictor.predict_injuries(
                tension_summary,
                video_analysis_temp,
                duration
            )

            # 3. Nine-box модель
            logger.info("Nine-box оценка...")
            nine_box_assessment = nine_box_model.assess_climber(
                video_analysis_temp,
                user_profile={}  # Пустой профиль, если не передан
            )
            
            # 4. НОВЫЕ МЕТРИКИ: Сводка по 7 базовым метрикам техники и дополнительным метрикам
            logger.info("Вычисление метрик техники...")
            
            # Средние значения метрик техники за всё видео
            avg_technique_metrics = {}
            if overlays.technique_metrics_history:
                for metric_name in ['quiet_feet', 'hip_position', 'diagonal', 'route_reading', 'rhythm', 'dynamic_control', 'grip_release']:
                    values = [m.get(metric_name, 50.0) for m in overlays.technique_metrics_history if metric_name in m]
                    if values:
                        avg_technique_metrics[metric_name] = sum(values) / len(values)
                    else:
                        avg_technique_metrics[metric_name] = 50.0
            else:
                # Дефолтные значения если нет истории
                avg_technique_metrics = {
                    'quiet_feet': 50.0, 'hip_position': 50.0, 'diagonal': 50.0,
                    'route_reading': 50.0, 'rhythm': 50.0, 'dynamic_control': 50.0, 'grip_release': 50.0
                }
            
            # Средние значения дополнительных метрик
            avg_additional_metrics = {}
            if overlays.additional_metrics_history:
                # Усредняем ВСЕ 8 метрик (включая productivity, economy, balance)
                for metric_name in ['stability', 'exhaustion', 'arm_efficiency', 'leg_efficiency', 'recovery', 'productivity', 'economy', 'balance']:
                    values = [m.get(metric_name, 50.0) for m in overlays.additional_metrics_history if metric_name in m]
                    if values:
                        avg_additional_metrics[metric_name] = sum(values) / len(values)
                    else:
                        avg_additional_metrics[metric_name] = 50.0
            else:
                avg_additional_metrics = {
                    'stability': 50.0, 'exhaustion': 0.0, 'arm_efficiency': 50.0,
                    'leg_efficiency': 50.0, 'recovery': 50.0,
                    'productivity': 50.0, 'economy': 50.0, 'balance': 50.0
                }
            
            # 5. SWOT-анализ
            logger.info("Генерация SWOT-анализа...")
            swot_analysis = swot_generator.generate_swot(
                avg_technique_metrics,
                avg_additional_metrics,
                tension_summary,
                {
                    'duration': duration,
                    'total_frames': total_frames,
                    'fps': fps
                }
            )
            
            # 6. Оценка уровня сложности
            estimated_grade = swot_generator.estimate_grade(avg_technique_metrics)
            
            logger.info(f"✅ Все алгоритмические анализы завершены. Оценка уровня: {estimated_grade}")

            # Полный результат
            result = {
                # Базовые данные
                'processed_video_path': str(output_path),
                'csv_path': str(csv_path),
                'duration': duration,
                'total_frames': total_frames,
                'processed_frames': processed_count,
                'fps': fps,
                
                # Базовая статистика
                **statistics,
                'best_frame': best_worst.get('best'),
                'worst_frame': best_worst.get('worst'),
                'technical_issues': technical_issues,
                
                # Падение
                'fall_detected': fall_detector.fall_detected,
                'fall_frame': fall_detector.fall_frame,
                'fall_timestamp': fall_detector.fall_timestamp,
                'fall_analysis': fall_detector.get_fall_analysis(),
                
                # BoulderVision метрики
                'bouldervision': {
                    'avg_velocity_ratio': bv_summary.get('avg_velocity_ratio', 1.0),
                    'max_velocity_ratio': bv_summary.get('max_velocity_ratio', 1.0),
                    'min_velocity_ratio': bv_summary.get('min_velocity_ratio', 1.0),
                    'velocity_std': bv_summary.get('velocity_std', 0.0),
                    'total_distance': bv_summary.get('total_distance', 0.0),
                    'avg_frame_distance': bv_summary.get('avg_frame_distance', 0.0),
                    'peak_velocity_frame': bv_summary.get('peak_velocity_frame'),
                    'slowest_frame': bv_summary.get('slowest_frame'),
                    'movement_pattern': bv_summary.get('movement_pattern', 'unknown'),
                    'time_zones': bv_summary.get('time_zones', {'lower':0,'middle':0,'upper':0})
                },

                # ========== НОВЫЕ АЛГОРИТМИЧЕСКИЕ АНАЛИЗЫ ==========

                # Анализ напряжения
                'tension_analysis': {
                    'overall_tension_index': tension_summary.get('overall_tension_index', 0),
                    'risk_level': tension_summary.get('risk_level', 'LOW'),
                    'zones': tension_summary.get('zones', {}),
                    'high_tension_moments': tension_summary.get('high_tension_moments', []),
                    'recommendations': tension_summary.get('recommendations', [])
                },

                # Прогноз травм
                'injury_prediction': {
                    'predictions': {
                        injury_type: {
                            'injury_type': pred.injury_type,
                            'body_part': pred.body_part,
                            'probability': pred.probability,
                            'risk_level': pred.risk_level.value,
                            'trauma_type': pred.trauma_type.value,
                            'timeline': pred.timeline,
                            'contributing_factors': pred.contributing_factors,
                            'prevention_measures': pred.prevention_measures,
                            'early_indicators': pred.early_indicators,
                            'self_test': pred.self_test
                        }
                        for injury_type, pred in injury_predictions.items()
                    },
                    'overall_risk': max(
                        [pred.probability for pred in injury_predictions.values()],
                        default=0.0
                    )
                },

                # Nine-box модель
                'nine_box': {
                    'skill_score': nine_box_assessment['scores']['skill'],
                    'physical_score': nine_box_assessment['scores']['physical'],
                    'mental_score': nine_box_assessment['scores']['mental'],
                    'category': nine_box_assessment['box_category'],
                    'label': nine_box_assessment['label'],
                    'description': nine_box_assessment['description'],
                    'position': nine_box_assessment['position'],
                    'recommendations': nine_box_assessment['recommendations'],
                    'ascii_plot': nine_box_assessment.get('ascii_plot', '')
                },

                # Анализ зацепов
                'holds_analysis': holds_analysis,
                
                # ========== НОВЫЕ МЕТРИКИ ТЕХНИКИ ==========
                'technique_metrics': avg_technique_metrics,
                'additional_metrics': avg_additional_metrics,
                'swot_analysis': swot_analysis,
                'estimated_grade': estimated_grade
            }
            
            # ========== ГЕНЕРАЦИЯ ДАШБОРДА ==========
            logger.info("Генерация дашборда...")
            try:
                # #region agent log
                with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"processor.py:398","message":"dashboard generation start","data":{},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                from app.reports.dashboard import DashboardGenerator
                
                # Подготавливаем данные для дашборда (НОВАЯ КОНЦЕПЦИЯ)
                dashboard_data = {
                    'duration': duration,
                    'avg_pose_quality': statistics.get('avg_pose_quality', 0),
                    'avg_motion_intensity': statistics.get('avg_motion_intensity', 0),
                    'avg_balance_score': statistics.get('avg_balance_score', 0),
                    'fall_detected': fall_detector.fall_detected,
                    'bouldervision': {
                        'velocity_history': bv_metrics.all_velocity_ratios[:200] if hasattr(bv_metrics, 'all_velocity_ratios') else []
                    },
                    'tension_analysis': {
                        'zones': tension_summary.get('zones', {})
                    },
                    'weight_distribution': {},
                    # НОВЫЕ МЕТРИКИ
                    'technique_metrics': avg_technique_metrics,
                    'additional_metrics': avg_additional_metrics,
                    'swot_analysis': swot_analysis,
                    'estimated_grade': estimated_grade,
                    # Старые метрики для обратной совместимости
                    'metrics': avg_technique_metrics  # Используем новые метрики как основные
                }
                
                dashboard_gen = DashboardGenerator()
                dashboard_path = TEMP_DIR / f"dashboard_{video_path.stem}.png"
                
                # #region agent log
                with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"processor.py:421","message":"dashboard generation before call","data":{"dashboard_path":str(dashboard_path),"has_metrics":bool(dashboard_data.get('metrics'))},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                
                dashboard_gen.generate_dashboard(dashboard_data, dashboard_path, format="png")
                
                # #region agent log
                with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"processor.py:428","message":"dashboard generation success","data":{"dashboard_path":str(dashboard_path),"file_exists":dashboard_path.exists()},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                
                result['dashboard_path'] = str(dashboard_path)
                logger.info(f"✅ Дашборд сохранен: {dashboard_path}")
            except Exception as e:
                # #region agent log
                with open('/home/user/с винды/ClimbAI/telegram_bot_bouldervision/.cursor/debug.log', 'a') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"processor.py:432","message":"dashboard generation error","data":{"error":str(e),"error_type":type(e).__name__},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                logger.warning(f"⚠️ Не удалось создать дашборд: {e}")
                result['dashboard_path'] = None
            
            logger.info("🎉 Обработка видео завершена успешно")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки видео: {e}", exc_info=True)
            raise
        
        finally:
            # КРИТИЧНО: Всегда освобождаем ресурсы, даже при ошибке
            if cap is not None:
                try:
                    cap.release()
                    logger.debug("✓ VideoCapture released")
                except Exception as e:
                    logger.warning(f"Не удалось освободить VideoCapture: {e}")
            
            if out is not None:
                try:
                    out.release()
                    logger.debug("✓ VideoWriter released")
                except Exception as e:
                    logger.warning(f"Не удалось освободить VideoWriter: {e}")
            
            if pose is not None:
                try:
                    pose.close()
                    logger.debug("✓ MediaPipe Pose closed")
                except Exception as e:
                    logger.warning(f"Не удалось закрыть MediaPipe Pose: {e}")
    
    def get_available_overlays(self) -> Dict[str, str]:
        """
        Возвращает список доступных типов визуализации
        
        Returns:
            dict с ключами-кодами и значениями-описаниями
        """
        overlays = {
            # Базовые (1-5)
            'skeleton': '🦴 Скелет - классическая визуализация',
            'points': '🎯 Точки - цветовая кодировка частей тела',
            'stress': '🔥 Напряжение - анализ углов суставов',
            'center': '📍 Центр масс - траектория движения',
            'metrics': '📊 Метрики - числовые показатели на видео',

            # BoulderVision (6-8)
            'heatmap': '🌡️ Тепловая карта - зоны концентрации',
            'trajectory': '📈 Траектория - полный путь движения',
        }

        # Добавляем holds только если есть детектор
        if self.holds_detector and self.holds_detector.is_initialized:
            overlays['holds'] = '🎯 Зацепы - детекция и связи с конечностями'
        else:
            overlays['holds'] = '🎯 Зацепы (требуется ROBOFLOW_API_KEY)'

        # Wow-Effect визуализации (9-12)
        overlays.update({
            'force_fingerprint': '💪 Силовой отпечаток - полярный график нагрузки',
            'decision_map': '🧠 Карта решений - моменты раздумий на трассе',
            'energy_profile': '🔋 Профиль энергии - истощение сил в реальном времени',
            'ghost_comparison': '👻 Призрак - сравнение с лучшей попыткой',
        })
        
        return overlays
