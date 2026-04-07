"""Entry point for DetermBot."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from src.core.agent import DeterministicCodeAgent
from src.core.consumers import Formatter

SUPPORTED_LANGUAGES = ("javascript", "typescript", "python", "go", "js", "ts", "py")


def _print_result(result, formatter: Formatter) -> None:
    """Print a single generation result."""
    if result.is_ambiguity and result.ambiguity:
        print(f"\nAMBIGUITY: {result.ambiguity.unclear_dimension}")
        print(f"QUESTION: {result.ambiguity.clarifying_question}")
        print(f"ASSUMED:  {result.ambiguity.assumed_interpretation}")
    elif result.sections:
        print(f"\n{formatter.format(result)}")
    else:
        print("\nNo output generated.")


def _read_language() -> str:
    """Prompt for target language with default."""
    lang = input("Language [javascript]: ").strip().lower()
    if not lang:
        return "javascript"
    if lang not in SUPPORTED_LANGUAGES:
        print(f"Unsupported language '{lang}'. Using javascript.")
        return "javascript"
    return lang


def _run_interactive(agent: DeterministicCodeAgent) -> None:
    """Interactive REPL loop."""
    formatter = Formatter()
    print("DetermBot — Deterministic Code Generator")
    print("Type your intent, or 'quit' to exit.\n")

    while True:
        try:
            intent = input("Intent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not intent or intent.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        language = _read_language()

        try:
            result = agent.generate(intent, language=language)
            _print_result(result, formatter)
        except ValueError as e:
            print(f"\nError: {e}")
        except RuntimeError as e:
            print(f"\nDeterminism violation: {e}")

        print()


def main() -> None:
    load_dotenv()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. See .env.example", file=sys.stderr)
        sys.exit(1)

    agent = DeterministicCodeAgent(api_key=api_key)

    # CLI mode: pass intent as arguments
    if len(sys.argv) > 1:
        intent = " ".join(sys.argv[1:])
        result = agent.generate(intent, language="javascript")
        formatter = Formatter()
        _print_result(result, formatter)
        return

    # Interactive mode
    _run_interactive(agent)


if __name__ == "__main__":
    main()
