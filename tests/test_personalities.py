from commentary.personalities import PERSONALITIES


class TestPersonalities:
    def test_all_have_required_keys(self):
        for name, p in PERSONALITIES.items():
            assert "name" in p
            assert "style" in p
            assert "catchphrases" in p
            assert isinstance(p["catchphrases"], list)

    def test_catchphrases_nonempty(self):
        for name, p in PERSONALITIES.items():
            assert len(p["catchphrases"]) > 0, f"{name} has no catchphrases"

    def test_known_personalities(self):
        expected = {"energetic", "chill", "sarcastic", "lore_keeper", "neuro"}
        assert set(PERSONALITIES.keys()) == expected
