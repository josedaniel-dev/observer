# LLM Observatory Python SDK

Open-source LLM observability SDK for tracing and monitoring AI applications.

## Installation

```bash
pip install llm-observatory
```

With optional integrations:

```bash
pip install llm-observatory[openai,anthropic,langchain]
```

## Quick Start

```python
from llm_observatory import instrument, trace

# Auto-instrument LLM libraries
instrument(openai=True, anthropic=True)

# Or manually trace functions
@trace(name="summarize")
def summarize(text: str):
    return openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": text}]
    )
```

## License

Apache License 2.0
