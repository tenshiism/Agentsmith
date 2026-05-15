import pytest
from agent.strategies import load_strategy, STRATEGIES


class TestStrategies:
    def test_load_known_strategies(self):
        for name in STRATEGIES:
            s = load_strategy(name)
            assert "system_prompt" in s
            assert "temperature" in s
            assert isinstance(s["temperature"], float)

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            load_strategy("nonexistent")

    def test_strategy_prompts_are_nonempty(self):
        for name, s in STRATEGIES.items():
            assert len(s["system_prompt"]) > 0, f"{name} has empty prompt"

    def test_temperature_ranges(self):
        for name, s in STRATEGIES.items():
            assert 0.0 <= s["temperature"] <= 2.0, f"{name} temp out of range"
