# LLM Observatory CLI

Command-line interface for LLM Observatory.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Start the server
llm-observatory serve

# Run an evaluation
llm-observatory evaluate --trace-id abc123 --evaluator llm_judge --criteria accuracy,safety

# Export traces
llm-observatory export --format json --output traces.json

# Check server status
llm-observatory status
```

## License

Apache License 2.0
