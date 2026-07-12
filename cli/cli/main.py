"""Main CLI application for LLM Observatory."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="llm-observatory")
def cli() -> None:
    """LLM Observatory CLI - Open-source LLM observability."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the observatory backend server."""
    import uvicorn

    console.print(f"[green]Starting LLM Observatory server on {host}:{port}[/green]")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
@click.option("--trace-id", required=True, help="Trace ID to evaluate")
@click.option(
    "--evaluator",
    type=click.Choice(["llm_judge", "rule_based", "human"]),
    required=True,
    help="Evaluator type",
)
@click.option("--criteria", help="Comma-separated criteria for evaluation")
@click.option("--endpoint", default="http://localhost:8000", help="API endpoint")
def evaluate(
    trace_id: str,
    evaluator: str,
    criteria: str | None,
    endpoint: str,
) -> None:
    """Run an evaluation on a trace."""
    import httpx

    console.print(f"[blue]Evaluating trace {trace_id} with {evaluator}...[/blue]")

    criteria_list = criteria.split(",") if criteria else []

    try:
        response = httpx.post(
            f"{endpoint}/v1/evaluations",
            json={
                "trace_id": trace_id,
                "evaluator_type": evaluator,
                "criteria": {"criteria": criteria_list} if criteria_list else None,
            },
        )
        response.raise_for_status()

        result = response.json()
        console.print("[green]Evaluation created successfully![/green]")
        console.print(f"ID: {result['id']}")
    except httpx.HTTPError as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="table")
@click.option("--limit", default=10, help="Number of traces to export")
@click.option("--offset", default=0, help="Offset for pagination")
@click.option("--endpoint", default="http://localhost:8000", help="API endpoint")
@click.option("--output", type=click.Path(), help="Output file path")
def export(
    output_format: str,
    limit: int,
    offset: int,
    endpoint: str,
    output: str | None,
) -> None:
    """Export traces from the observatory."""
    import json

    import httpx

    console.print(f"[blue]Exporting traces (limit={limit}, offset={offset})...[/blue]")

    try:
        response = httpx.get(
            f"{endpoint}/v1/traces",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()

        traces = response.json()

        if output_format == "json":
            data = json.dumps(traces, indent=2, default=str)
            if output:
                with open(output, "w") as f:
                    f.write(data)
                console.print(f"[green]Exported to {output}[/green]")
            else:
                console.print(data)
        else:
            table = Table(title="Traces")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Created", style="blue")

            for trace in traces:
                table.add_row(
                    trace["id"][:8],
                    trace["name"],
                    trace["status"],
                    str(trace.get("created_at", "")),
                )

            console.print(table)

    except httpx.HTTPError as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option("--endpoint", default="http://localhost:8000", help="API endpoint")
def status(endpoint: str) -> None:
    """Check the status of the observatory server."""
    import httpx

    try:
        response = httpx.get(f"{endpoint}/health")
        response.raise_for_status()

        console.print("[green]Server is healthy![/green]")
        console.print(f"Endpoint: {endpoint}")
    except httpx.HTTPError:
        console.print("[red]Server is not responding[/red]")


if __name__ == "__main__":
    cli()
