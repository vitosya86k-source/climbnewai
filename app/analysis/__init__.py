"""Модуль анализа видео"""

from .frame_analyzer import FrameAnalyzer
from .fall_detector import FallDetector
from .csv_generator import generate_csv_report
from .tension_analyzer import BodyTensionAnalyzer
from .injury_predictor import InjuryPredictor, InjuryPrediction, RiskLevel, TraumaType
from .nine_box_model import ClimberNineBoxModel
from .route_assessor import RouteAssessor, RouteAssessment, RouteAssessmentType, BottleneckFactor
from .algorithmic import AlgorithmicAnalyzer, generate_algorithmic_report
from .ai_recommendations import AIRecommendationEngine, get_ai_recommendations

__all__ = [
    "FrameAnalyzer",
    "FallDetector",
    "generate_csv_report",
    "BodyTensionAnalyzer",
    "InjuryPredictor",
    "InjuryPrediction",
    "RiskLevel",
    "TraumaType",
    "ClimberNineBoxModel",
    "RouteAssessor",
    "RouteAssessment",
    "RouteAssessmentType",
    "BottleneckFactor",
    "AlgorithmicAnalyzer",
    "generate_algorithmic_report",
    "AIRecommendationEngine",
    "get_ai_recommendations"
]


