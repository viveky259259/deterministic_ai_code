"""Tests for main.py entry point."""

from unittest.mock import MagicMock, patch

import pytest


def _make_success_result():
    result = MagicMock()
    result.is_ambiguity = False
    result.sections = MagicMock()
    result.sections.implementation = "const total = (a, b) => a + b;"
    result.sections.intent_classification = "type: PURE_FUNCTION"
    result.sections.signature = "javascript: const total = (a, b) => a + b"
    result.sections.invariants = "preconditions: inputs are numbers"
    result.sections.test_oracle = "assert(total(1, 2) === 3);"
    result.sections.dependencies = None
    result.content_hash = "abcdef1234567890"
    return result


def _make_ambiguity_result():
    result = MagicMock()
    result.is_ambiguity = True
    result.ambiguity = MagicMock()
    result.ambiguity.unclear_dimension = "unknown verb"
    result.ambiguity.clarifying_question = "What type?"
    result.ambiguity.assumed_interpretation = "Assuming PURE_FUNCTION"
    result.sections = None
    return result


class TestMain:
    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_main_cli_mode(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.return_value = _make_success_result()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        with patch("sys.argv", ["main", "check", "if", "even"]):
            main()

        mock_agent.generate.assert_called_once_with("check if even", language="javascript")

    @patch("src.main.load_dotenv")
    @patch("src.main.os.environ", {})
    def test_main_exits_without_api_key(self, _mock_dotenv):
        from src.main import main

        with pytest.raises(SystemExit):
            main()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_main_cli_ambiguity_output(self, mock_agent_cls, capsys):
        mock_agent = MagicMock()
        mock_agent.generate.return_value = _make_ambiguity_result()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        with patch("sys.argv", ["main", "frobnicate"]):
            main()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_quit(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=["quit"]):
            main()

        mock_agent.generate.assert_not_called()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_generate_then_quit(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.return_value = _make_success_result()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        inputs = ["write add function", "javascript", "quit"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()

        mock_agent.generate.assert_called_once_with("write add function", language="javascript")

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_default_language(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.return_value = _make_success_result()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        # Empty language input → defaults to javascript
        inputs = ["write add function", "", "exit"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()

        mock_agent.generate.assert_called_once_with("write add function", language="javascript")

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_python_language(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.return_value = _make_success_result()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        inputs = ["write add function", "python", "q"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()

        mock_agent.generate.assert_called_once_with("write add function", language="python")

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_unsupported_language_falls_back(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.return_value = _make_success_result()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        inputs = ["write add function", "rust", "q"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()

        mock_agent.generate.assert_called_once_with("write add function", language="javascript")

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_eof_exits(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=EOFError):
            main()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_keyboard_interrupt_exits(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=KeyboardInterrupt):
            main()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_value_error(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.side_effect = ValueError("Intent too short")
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        inputs = ["ab", "javascript", "quit"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_runtime_error(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.side_effect = RuntimeError("DETERMINISM_VIOLATION")
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        inputs = ["write add function", "javascript", "quit"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_ambiguity_output(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent.generate.return_value = _make_ambiguity_result()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        inputs = ["frobnicate stuff", "javascript", "quit"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_empty_intent_exits(self, mock_agent_cls):
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=[""]):
            main()

        mock_agent.generate.assert_not_called()

    @patch("src.main.DeterministicCodeAgent")
    @patch("src.main.os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_interactive_no_sections_result(self, mock_agent_cls):
        mock_agent = MagicMock()
        result = MagicMock()
        result.is_ambiguity = False
        result.sections = None
        result.ambiguity = None
        mock_agent.generate.return_value = result
        mock_agent_cls.return_value = mock_agent

        from src.main import main

        inputs = ["write add function", "js", "quit"]
        with patch("sys.argv", ["main"]), patch("builtins.input", side_effect=inputs):
            main()
