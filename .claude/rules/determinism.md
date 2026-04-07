---
paths: ["src/**/*.py"]
---

# Determinism Rules

## LLM Calls
- Always set `temperature=0` unless explicitly overridden by the caller
- Use fixed `seed` parameter when the model supports it
- Cache responses keyed on (model, messages_hash, temperature, seed) for replay
- Log the exact request payload so calls can be reproduced

## Code Generation
- No randomness without explicit seeding (random.seed, np.random.seed)
- Sort all dict/set iterations that affect output ordering
- Use deterministic hash functions (hashlib, not hash())
- Timestamp-dependent logic must accept injectable clocks for testing

## Testing for Determinism
- Snapshot tests: run the same input twice, assert identical output
- All tests must pass with `PYTHONHASHSEED=0`
