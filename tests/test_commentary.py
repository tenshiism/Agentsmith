from unittest.mock import Mock
from commentary.generator import CommentaryGenerator


class TestCommentaryGenerator:
    def test_speak_returns_text(self):
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}})
        result = cg.speak("hello world")
        assert result == "hello world"

    def test_speak_dedup(self):
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}})
        cg.speak("duplicate")
        result = cg.speak("duplicate")
        assert result is None

    def test_speak_empty_returns_none(self):
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}})
        result = cg.speak("")
        assert result is None

    def test_speak_calls_tts(self):
        tts_mock = Mock()
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}}, tts=tts_mock)
        cg.speak("test")
        tts_mock.say.assert_called_once_with("test")

    def test_speak_no_tts(self):
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}})
        cg.speak("no tts")
        assert cg.last_comment == "no tts"

    def test_build_context_positive_reward(self):
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}})
        state = Mock(reward=50)
        text = cg.build_commentary_context(state)
        assert "Big score" in text

    def test_build_context_negative_reward(self):
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}})
        state = Mock(reward=-10)
        text = cg.build_commentary_context(state)
        assert "Ouch" in text

    def test_build_context_neutral_reward(self):
        cg = CommentaryGenerator({"commentary": {"personality": "chill"}})
        state = Mock(reward=0)
        text = cg.build_commentary_context(state)
        assert text == ""
