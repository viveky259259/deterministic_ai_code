# Base Project Prompt

## How to Run

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 4. Run the app
python -m src.main
```

## How to Test

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_llm_client.py -v

# Run tests matching a pattern
python -m pytest tests/ -k "test_logging" -v

# Run with deterministic hash seed (validates determinism)
PYTHONHASHSEED=0 python -m pytest tests/ -v
```

## Project Structure

```
src/
  __init__.py
  main.py              # Entry point
  core/                # Deterministic execution engine
  logging/             # LLM call and prompt logging
  observability/       # Tracing, metrics, structured logs
  context/             # Context window management and compaction
  agents/              # Sub-agent orchestration
tests/
  __init__.py
  test_*.py            # Mirror src/ structure
.env.example           # Required environment variables
requirements.txt       # Python dependencies
```

## Key Commands

| Task | Command |
|------|---------|
| Run app | `python -m src.main` |
| Run tests | `python -m pytest tests/ -v` |
| Lint | `ruff check src/ tests/` |
| Format | `black src/ tests/` |
| Type check | `mypy src/` |
| Coverage | `python -m pytest --cov=src` |
