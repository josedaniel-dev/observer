# LLM Observatory

Open-source observability and telemetry platform for analyzing and grading LLMs.

## Features

- **Multi-framework tracing** - Auto-instrument OpenAI, Anthropic, LangChain, and more
- **Cost tracking** - Monitor token usage and costs across models
- **Evaluation engine** - LLM-as-Judge, rule-based metrics, and human feedback
- **Real-time dashboard** - Live trace streaming via WebSocket
- **CLI tools** - Manage and query traces from the terminal

## Quick Start

### Using Docker Compose

```bash
docker-compose up -d
```

### Manual Setup

1. Start PostgreSQL:

```bash
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=observatory postgres:16
```

2. Install and run the backend:

```bash
cd backend
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

3. Start the dashboard:

```bash
cd dashboard
npm install
npm run dev
```

## Python SDK

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

## TypeScript SDK

```typescript
import { instrument, trace } from 'llm-observatory';

instrument({ openai: true });

const summarize = trace('summarize', async (text: string) => {
  return await openai.chat.completions.create({
    model: 'gpt-4',
    messages: [{ role: 'user', content: text }]
  });
});
```

## CLI

```bash
# Start the server
llm-observatory serve

# Run an evaluation
llm-observatory evaluate --trace-id abc123 --criteria accuracy,safety

# Export traces
llm-observatory export --format json --output traces.json
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLM Observatory                          │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  Python SDK  │ TypeScript   │   Backend    │    Dashboard      │
│              │ SDK          │  (FastAPI)   │    (React)        │
└──────────────┴──────────────┴──────────────┴───────────────────┘
        │              │             │               │
        └──────────────┴─────────────┴───────────────┘
                              │
                   ┌──────────┴──────────┐
                   │    PostgreSQL       │
                   └─────────────────────┘
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
