#!/usr/bin/env python3
"""
Тест структуры данных nine_box
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.analysis.nine_box_model import ClimberNineBoxModel

# Создаем экземпляр
model = ClimberNineBoxModel()

# Тестовые данные
test_video_analysis = {
    'duration': 30,
    'fps': 30,
    'total_frames': 900,
    'avg_pose_quality': 85,
    'avg_motion_intensity': 25,
    'avg_balance_score': 70,
    'fall_detected': False,
    'bouldervision': {
        'avg_velocity_ratio': 1.2,
        'trajectory_efficiency': 0.7,
        'straight_arms_efficiency': 0.65,
        'velocity_std': 0.8,
        'total_distance': 15.0,
        'time_in_power_zone': 0.25,
        'time_in_endurance_zone': 0.40,
        'time_in_recovery_zone': 0.35
    },
    'tension_analysis': {
        'overall_tension': 'MODERATE',
        'zones': {
            'forearms': {'high_percent': 25},
            'shoulders': {'high_percent': 20},
            'lumbar': {'high_percent': 15},
            'knees': {'high_percent': 10}
        }
    }
}

test_user_profile = {}

print("🔍 Тестирование структуры nine_box_assessment\n")
print("=" * 60)

# Вызываем assess_climber
result = model.assess_climber(test_video_analysis, test_user_profile)

print("\n✅ Метод assess_climber выполнен успешно")
print("\n📊 Возвращаемые ключи:")
for key in result.keys():
    print(f"   • {key}")

print("\n📋 Полная структура:")
print(f"   box_category: {result['box_category']}")
print(f"   label: {result['label']}")
print(f"   description: {result['description']}")
print(f"   scores: {result['scores']}")
print(f"   position: {result['position']}")
print(f"   recommendations: {result['recommendations'][:2]}")
print(f"   ascii_plot: {'Присутствует' if result.get('ascii_plot') else 'Отсутствует'}")

print("\n" + "=" * 60)
print("✅ СТРУКТУРА ДАННЫХ КОРРЕКТНА")
print("=" * 60)

# Проверяем что processor.py ожидает правильные ключи
print("\n🔧 Проверка совместимости с processor.py:")
try:
    skill_score = result['scores']['skill']
    physical_score = result['scores']['physical']
    mental_score = result['scores']['mental']
    category = result['box_category']
    label = result['label']
    description = result['description']
    position = result['position']
    recommendations = result['recommendations']
    ascii_plot = result.get('ascii_plot', '')

    print("   ✅ Все ожидаемые ключи присутствуют")
    print(f"   ✅ skill_score: {skill_score:.1f}")
    print(f"   ✅ physical_score: {physical_score:.1f}")
    print(f"   ✅ mental_score: {mental_score:.1f}")
    print(f"   ✅ category: {category}")
    print(f"   ✅ label: {label}")

except KeyError as e:
    print(f"   ❌ ОШИБКА: Отсутствует ключ {e}")
    sys.exit(1)

print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
