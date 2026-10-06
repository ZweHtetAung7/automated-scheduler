import pytest

from app.scheduler.defaults import DEFAULT_SETTINGS, effective_settings


def test_balanced_weights_sum_to_one() -> None:
    weights = [v for k, v in DEFAULT_SETTINGS.items() if k.startswith("weights.")]
    base = sum(weights) - DEFAULT_SETTINGS["weights.important_bonus"]
    assert base == pytest.approx(1.0)


def test_overrides_replace_only_changed_keys() -> None:
    settings = effective_settings({"study.max_hours_per_day": 4})
    assert settings["study.max_hours_per_day"] == 4
    assert settings["sleep.wake_time"] == DEFAULT_SETTINGS["sleep.wake_time"]


def test_unknown_override_is_rejected() -> None:
    with pytest.raises(KeyError):
        effective_settings({"study.max_hours_per_week": 30})
