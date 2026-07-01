import sys
import argparse
from urllib.parse import urlparse

import requests
import config

_MODEL_SHORTHANDS = {
    "3b": "qwen2.5-coder:3b",
    "7b": "qwen2.5-coder:7b",
}
from benchmark import run_benchmark
from rich.panel import Panel
from runner import console, run_single, run_freeform


def _check_services():
    ok = True
    try:
        requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
    except requests.ConnectionError:
        console.print(f"[yellow]Warning: Ollama not reachable at {config.OLLAMA_BASE_URL}[/yellow]")
        ok = False
    try:
        p = urlparse(config.GRAPHDB_ENDPOINT)
        requests.get(f"{p.scheme}://{p.netloc}", timeout=3)
    except requests.ConnectionError:
        console.print(f"[yellow]Warning: GraphDB not reachable at {config.GRAPHDB_ENDPOINT}[/yellow]")
        ok = False
    return ok


def print_menu():
    menu = (
        "  [bold cyan]S[/bold cyan]  Single question\n"
        "  [bold cyan]F[/bold cyan]  Free-form question\n"
        "  [bold cyan]B[/bold cyan]  Benchmark\n"
        "  [bold cyan]Q[/bold cyan]  Quit"
    )
    console.print(Panel(menu, title="[bold]Geographic Ontology NLQ Tester[/bold]", border_style="cyan"))


def main():
    console.print(f"[dim]Model  :[/dim] [bold]{config.OLLAMA_MODEL}[/bold]")
    console.print(f"[dim]GraphDB:[/dim] [bold]{config.GRAPHDB_ENDPOINT}[/bold]")
    _check_services()

    while True:
        print_menu()
        choice = input("Select: ").strip().upper()

        if choice == "Q":
            console.print("[dim]Goodbye.[/dim]")
            sys.exit(0)
        elif choice == "S":
            run_single()
        elif choice == "F":
            run_freeform()
        elif choice == "B":
            run_benchmark()
        else:
            console.print("[red]Invalid selection.[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Geographic Ontology NLQ Tester")
    parser.add_argument(
        "--model",
        default=None,
        metavar="NAME",
        help="Model to use (e.g. 3b, 7b, or a full Ollama model name). Defaults to config.py.",
    )
    args = parser.parse_args()
    if args.model is not None:
        config.OLLAMA_MODEL = _MODEL_SHORTHANDS.get(args.model, args.model)
    main()
