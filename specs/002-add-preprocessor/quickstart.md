# Quickstart: Validating the Pre-Processor Module

## Prerequisites

- Python 3.11+ with `uv` installed
- Project dependencies installed: `uv sync`
- Either an Anthropic API key stored in the system keychain (`provider/claude`) **or** Ollama running locally with `qwen2.5:3b` pulled

## Run Unit Tests

```bash
uv run pytest tests/unit/processing/test_preprocessor.py -v
```

**Expected outcome**: All tests pass, including:
- Stage 1: filler removal, Haiku selection, Ollama fallback
- Stage 2: 4Ds structuring, JSON output shape, `incomplete` flag, empty input, JSON retry behaviour

## Run the Module in Isolation

```python
import asyncio
from src.processing.preprocessor import Preprocessor

async def main():
    pp = Preprocessor()
    result = await pp.process("uh, like, book a flight to Lisbon next Friday please, under 500 euros")
    print(result.structured_prompt.to_dict())
    print(f"Model: {result.model_used}")
    print(f"Total latency: {result.total_latency_ms:.0f}ms")

asyncio.run(main())
```

**Expected output** (shape — content will vary by model):
```json
{
  "task": "Book a flight to Lisbon on Friday",
  "context": "Travel date: next Friday; budget constraint: 500 euros",
  "constraints": "Budget must not exceed 500 euros",
  "expected_output": "Flight options with price and departure time",
  "incomplete": false
}
```

## Validate Edge Cases

### Empty input
```python
result = await pp.process("")
assert result.structured_prompt.task == ""
assert result.structured_prompt.incomplete == False
assert result.error is None
```

### Filler-words-only input
```python
result = await pp.process("uh... um... hm...")
# Stage 1 cleans to empty; Stage 2 returns empty StructuredPrompt
assert result.structured_prompt.task == ""
assert result.structured_prompt.incomplete == True
```

### Incomplete request
```python
result = await pp.process("remind me")
assert result.structured_prompt.incomplete == True
```

## Validate Audit Logs

Start the module with JSON logging enabled:
```bash
uv run python -c "
from src.memory.audit import configure_logging
configure_logging(level='INFO', fmt='json')
import asyncio
from src.processing.preprocessor import Preprocessor
async def main():
    pp = Preprocessor()
    await pp.process('set a timer for five minutes')
asyncio.run(main())
"
```

**Expected**: Two JSON log lines emitted — one with `event: preprocessor_stage1`, one with `event: preprocessor_stage2`.

## Validate Pipeline Integration

Run the full pipeline integration test:
```bash
uv run pytest tests/integration/test_audio_pipeline.py -v -k preprocessor
```

**Expected**: The pre-processor stage in the pipeline receives a raw transcript and delivers a `PreProcessorResult` to the classifier.

## Performance Check

```bash
uv run python -c "
import asyncio, time
from src.processing.preprocessor import Preprocessor

async def main():
    pp = Preprocessor()
    start = time.perf_counter()
    result = await pp.process('open my calendar and schedule a meeting with John tomorrow at 2pm')
    elapsed = (time.perf_counter() - start) * 1000
    print(f'Total wall time: {elapsed:.0f}ms')
    print(f'Module reported: {result.total_latency_ms:.0f}ms')
    assert result.total_latency_ms < 2000, 'Exceeds 2-second budget'
    print('Performance check: PASS')

asyncio.run(main())
"
```
