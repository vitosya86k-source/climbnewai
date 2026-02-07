"""CRUD операции для БД"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
import logging

from .models import User, Video, VideoExport, Progress
from app.config import FREE_VIDEO_LIMIT

logger = logging.getLogger(__name__)


# ============= USER =============

def get_or_create_user(session: Session, telegram_id: int, username: str = None, name: str = None) -> User:
    """Получить или создать пользователя"""
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            name=name,
            free_videos_left=FREE_VIDEO_LIMIT
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Создан новый пользователь: {telegram_id}")
    else:
        # Обновляем username и name если изменились
        if username and user.username != username:
            user.username = username
        if name and user.name != name:
            user.name = name
        session.commit()
    
    return user


def update_user_videos_count(session: Session, user_id: int):
    """Обновить счетчик проанализированных видео"""
    user = session.query(User).filter(User.id == user_id).first()
    if user:
        user.videos_analyzed += 1
        if not user.is_premium and user.free_videos_left > 0:
            user.free_videos_left -= 1
        session.commit()


def can_analyze_video(session: Session, user_id: int) -> bool:
    """Проверить, может ли пользователь анализировать видео"""
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    if user.is_premium:
        return True
    
    return user.free_videos_left > 0


# ============= VIDEO =============

def create_video(session: Session, user_id: int, telegram_file_id: str) -> Video:
    """Создать запись видео"""
    video = Video(
        user_id=user_id,
        telegram_file_id=telegram_file_id
    )
    session.add(video)
    session.commit()
    session.refresh(video)
    logger.info(f"Создано видео: {video.id} для пользователя {user_id}")
    return video


def update_video_analysis(
    session: Session,
    video_id: int,
    analysis_data: dict,
    csv_path: str = None
) -> Video:
    """Обновить видео результатами анализа"""
    video = session.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Видео {video_id} не найдено")
    
    video.processed = True
    video.analysis_data = analysis_data
    video.csv_path = csv_path
    
    # Извлекаем ключевые метрики
    video.duration = analysis_data.get('duration')
    video.total_frames = analysis_data.get('total_frames')
    video.avg_pose_quality = analysis_data.get('avg_pose_quality')
    video.avg_motion_intensity = analysis_data.get('avg_motion_intensity')
    video.overall_quality = analysis_data.get('overall_quality')
    
    # Падения
    video.fall_detected = analysis_data.get('fall_detected', False)
    video.fall_timestamp = analysis_data.get('fall_timestamp')
    video.fall_frame = analysis_data.get('fall_frame')
    
    session.commit()
    session.refresh(video)
    return video


def update_video_report(
    session: Session,
    video_id: int,
    report_text: str,
    report_format: str,
    expert_assigned: str = None,
    expert_score: float = None,
    neuro_type: str = None
) -> Video:
    """Обновить видео отчетом"""
    video = session.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Видео {video_id} не найдено")
    
    video.report_text = report_text
    video.report_format = report_format
    video.expert_assigned = expert_assigned
    video.expert_score = expert_score
    video.neuro_type = neuro_type
    
    session.commit()
    session.refresh(video)
    return video


def get_user_videos(session: Session, user_id: int, limit: int = 10) -> List[Video]:
    """Получить видео пользователя"""
    return session.query(Video).filter(
        Video.user_id == user_id,
        Video.processed == True
    ).order_by(Video.uploaded_at.desc()).limit(limit).all()


# ============= VIDEO EXPORT =============

def create_video_export(
    session: Session,
    video_id: int,
    overlay_type: str,
    telegram_file_id: str
) -> VideoExport:
    """Создать экспорт видео"""
    export = VideoExport(
        video_id=video_id,
        overlay_type=overlay_type,
        telegram_file_id=telegram_file_id
    )
    session.add(export)
    session.commit()
    session.refresh(export)
    return export


# ============= PROGRESS =============

def create_progress_record(
    session: Session,
    user_id: int,
    video_id: int,
    analysis_data: dict
) -> Progress:
    """Создать запись прогресса"""
    # Вычисляем улучшение по сравнению с предыдущим видео
    previous = session.query(Progress).filter(
        Progress.user_id == user_id
    ).order_by(Progress.recorded_at.desc()).first()
    
    improvement = None
    if previous and previous.avg_pose_quality:
        current_quality = analysis_data.get('avg_pose_quality', 0)
        improvement = ((current_quality - previous.avg_pose_quality) / previous.avg_pose_quality) * 100
    
    progress = Progress(
        user_id=user_id,
        video_id=video_id,
        avg_pose_quality=analysis_data.get('avg_pose_quality'),
        avg_motion_intensity=analysis_data.get('avg_motion_intensity'),
        fall_count=1 if analysis_data.get('fall_detected') else 0,
        avg_balance_score=analysis_data.get('avg_balance_score'),
        technical_issues=analysis_data.get('technical_issues', {}),
        improvement_percent=improvement
    )
    
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


def get_user_progress(session: Session, user_id: int, limit: int = 10) -> List[Progress]:
    """Получить историю прогресса пользователя"""
    return session.query(Progress).filter(
        Progress.user_id == user_id
    ).order_by(Progress.recorded_at.desc()).limit(limit).all()


