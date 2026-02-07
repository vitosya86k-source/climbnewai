"""SQLAlchemy модели"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Premium статус
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime, nullable=True)
    
    # Лимиты
    videos_analyzed = Column(Integer, default=0)
    free_videos_left = Column(Integer, default=3)
    
    # Связи
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Video(Base):
    """Модель видео"""
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    
    # Файлы
    telegram_file_id = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed = Column(Boolean, default=False)
    
    # Базовые метрики
    duration = Column(Float)
    total_frames = Column(Integer)
    avg_pose_quality = Column(Float, index=True)
    avg_motion_intensity = Column(Float)
    overall_quality = Column(Float)
    
    # BoulderVision метрики
    avg_velocity_ratio = Column(Float, nullable=True)      # Средний Velocity Ratio
    max_velocity_ratio = Column(Float, nullable=True)      # Максимальный VR
    total_distance = Column(Float, nullable=True)          # Накопленная дистанция
    movement_pattern = Column(String, nullable=True)       # Паттерн движения
    time_in_upper_zone = Column(Float, nullable=True)      # % времени в верхней зоне
    time_in_middle_zone = Column(Float, nullable=True)     # % времени в средней зоне
    time_in_lower_zone = Column(Float, nullable=True)      # % времени в нижней зоне
    
    # Анализ зацепов (если включена детекция)
    holds_used_count = Column(Integer, nullable=True)      # Количество использованных зацепов
    longest_hold_time = Column(Float, nullable=True)       # Время на самом долгом зацепе
    longest_hold_color = Column(String, nullable=True)     # Цвет самого долгого зацепа
    holds_analysis_data = Column(JSON, nullable=True)      # Полные данные по зацепам
    
    # Падения
    fall_detected = Column(Boolean, default=False)
    fall_timestamp = Column(Float, nullable=True)
    fall_frame = Column(Integer, nullable=True)
    
    # Экспертиза
    expert_assigned = Column(String)  # Какой эксперт дал оценку
    expert_score = Column(Float)
    
    # Психология
    neuro_type = Column(String)  # ФИЛОСОФ/ВОИН/АНАЛИТИК/СПРИНТЕР
    
    # Полные данные
    analysis_data = Column(JSON)  # Весь анализ
    csv_path = Column(String)     # Путь к CSV
    
    # Отчеты
    report_format = Column(String)
    report_text = Column(Text)
    
    # Связи
    user = relationship("User", back_populates="videos")
    video_exports = relationship("VideoExport", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Video(id={self.id}, user_id={self.user_id}, processed={self.processed})>"


class VideoExport(Base):
    """Таблица для хранения разных разметок одного видео"""
    __tablename__ = 'video_exports'
    
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), index=True)
    
    overlay_type = Column(String, nullable=False)  # skeleton, stress, etc.
    telegram_file_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    video = relationship("Video", back_populates="video_exports")
    
    def __repr__(self):
        return f"<VideoExport(id={self.id}, video_id={self.video_id}, type={self.overlay_type})>"


class Progress(Base):
    """Модель прогресса пользователя"""
    __tablename__ = 'progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    video_id = Column(Integer, ForeignKey('videos.id'))
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Ключевые метрики для графиков
    avg_pose_quality = Column(Float)
    avg_motion_intensity = Column(Float)
    fall_count = Column(Integer, default=0)
    avg_balance_score = Column(Float)
    
    # Технические проблемы (для отслеживания улучшений)
    technical_issues = Column(JSON)  # {"elbow_bend": 5, "shoulder_angles": 3}
    
    # Сравнение с предыдущей сессией
    improvement_percent = Column(Float, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="progress_records")
    
    def __repr__(self):
        return f"<Progress(id={self.id}, user_id={self.user_id}, quality={self.avg_pose_quality})>"


