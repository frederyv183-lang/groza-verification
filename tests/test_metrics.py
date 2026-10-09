"""
Тесты метрик.
"""
from src.metrics.verification import all_metrics, confusion_matrix


def test_confusion_matrix():
    cm = confusion_matrix([1, 0, 1, 0], [1, 1, 0, 0])
    assert cm["hits"] == 1
    assert cm["misses"] == 1
    assert cm["false_alarms"] == 1
    assert cm["correct_negatives"] == 1


def test_perfect_forecast():
    m = all_metrics([1, 0, 1, 0], [1, 0, 1, 0])
    assert m["POD"] == 1.0
    assert m["FAR"] == 0.0
    assert m["CSI"] == 1.0
    assert m["HK"] == 1.0


def test_all_misses():
    m = all_metrics([1, 1], [0, 0])
    assert m["POD"] == 0.0
    assert m["CSI"] == 0.0
