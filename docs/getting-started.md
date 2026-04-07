# Getting Started

This guide provides instructions on how to set up and run the DetermBot project.

## Prerequisites

- Python 3.11+

## Setup

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root of the project and add the following environment variables. You can use the `.env.example` file as a template.
    ```
    ANTHROPIC_API_KEY=your_api_key
    ```

## Running the Agent

To run the DetermBot agent, use the following command:

```bash
python -m src.main
```

## Testing

To run the test suite, use the following command:

```bash
python -m pytest tests/ -v
```

### Test Coverage

To run tests with coverage, use the following command:

```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Specific Tests

To run a specific test file, use the following command:

```bash
python -m pytest tests/test_contracts.py -v
```

### Determinism Regression

To run the determinism regression tests, use the following command:

```bash
PYTHONHASHSEED=0 python -m pytest tests/ -v
```

## Linting and Type Checking

To lint and type check the code, use the following commands:

```bash
ruff check src/ tests/
mypy src/
```
