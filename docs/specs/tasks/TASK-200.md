# TASK-200: Update LLM Configuration

**Status:** NOT STARTED
**Created:** February 2, 2026
**Completed:** N/A
**Priority:** High (do before Strategist)
**Depends On:** None
**Phase:** Phase 2.2 - Strategist Integration

---

## Objective

Switch from `qwen2.5-coder:7b` to `qwen2.5:14b` for better reasoning capabilities in trade analysis and strategy generation.

---

## Background

The current system uses `qwen2.5-coder:7b`, which is optimized for code generation. For the Strategist component (TASK-110), we need:

- Better market analysis reasoning
- More nuanced trade condition generation
- Improved pattern recognition explanations
- Higher quality reflection insights

The `qwen2.5:14b` model (already installed on the system) provides:
- 2x more parameters for deeper reasoning
- General-purpose training vs code-focused
- Better natural language understanding for market context

---

## Specification

### Current Configuration

Located in `src/llm_interface.py`:

```python
DEFAULT_MODEL = "qwen2.5-coder:7b"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "172.27.144.1")
DEFAULT_API_URL = f"http://{OLLAMA_HOST}:11434/api/chat"
```

### Target Configuration

```python
DEFAULT_MODEL = "qwen2.5:14b"
# Keep OLLAMA_HOST and API_URL unchanged
```

### Optional: Model Selection by Task

For future flexibility, consider making model configurable per task type:

```python
MODEL_CONFIG = {
    "default": "qwen2.5:14b",
    "code_generation": "qwen2.5-coder:7b",  # If we need code output
    "analysis": "qwen2.5:14b",
    "reflection": "qwen2.5:14b",
}
```

---

## Technical Approach

### Step 1: Verify Model Available

```bash
ollama list | grep qwen2.5:14b
```

### Step 2: Update Default Model

Edit `src/llm_interface.py`:
```python
DEFAULT_MODEL = "qwen2.5:14b"
```

### Step 3: Update Documentation

- Update docstrings referencing model name
- Update any comments mentioning model

### Step 4: Test LLM Interface

```bash
python -c "
from src.llm_interface import LLMInterface
llm = LLMInterface()
print(f'Model: {llm.model}')
response = llm.query('What is 2+2?')
print(f'Response: {response}')
"
```

### Step 5: Benchmark Response Quality

Compare old vs new model on sample prompts:
- Market analysis prompt
- Trade condition generation prompt
- Reflection prompt

---

## Files Modified

| File | Change |
|------|--------|
| `src/llm_interface.py` | Update DEFAULT_MODEL constant |

---

## Acceptance Criteria

- [ ] `qwen2.5:14b` is set as default model
- [ ] LLM interface initializes successfully
- [ ] Basic query returns valid response
- [ ] Response quality tested on trading-related prompts
- [ ] No breaking changes to existing code

---

## Verification

```bash
# Verify model loads
python -c "
from src.llm_interface import LLMInterface
llm = LLMInterface()
assert llm.model == 'qwen2.5:14b', f'Expected qwen2.5:14b, got {llm.model}'
print('Model configured correctly')

# Test basic functionality
response = llm.query('Analyze BTC price action: up 5% in 1 hour with high volume')
print(f'Response length: {len(response)} chars')
assert len(response) > 50, 'Response too short'
print('LLM responding correctly')
"
```

---

## Completion Notes

*To be filled after implementation*

---

## Related

- [TASK-110](./TASK-110.md) - Strategist Component (uses this model)
- [TASK-130](./TASK-130.md) - Reflection Engine (uses this model)
- [PHASE-2-INDEX.md](../PHASE-2-INDEX.md) - Phase overview
