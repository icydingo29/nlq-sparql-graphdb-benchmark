import requests
from rich.console import Console
from rich.syntax import Syntax

import graphdb
import llm
import reference_questions as qbank

console = Console()
MAX_RETRIES = 2


# ── execution helpers ─────────────────────────────────────────────────────────

def _execute_with_retry(question: str, sparql: str, verbose: bool = True) -> tuple:
    attempt = 0
    while True:
        attempt += 1
        try:
            rows = graphdb.query(sparql)
            return sparql, graphdb.extract_values(rows), attempt
        except requests.ConnectionError:
            raise RuntimeError("Cannot reach GraphDB — is it running on port 7200?")
        except requests.HTTPError as exc:
            is_syntax_error = exc.response is not None and exc.response.status_code == 400
            if is_syntax_error and attempt <= MAX_RETRIES:
                error_hint = exc.response.text[:300] if (exc.response is not None and exc.response.text) else str(exc)
                if verbose:
                    console.print(f"\n  [yellow][[Retry {attempt}/{MAX_RETRIES} — syntax error, asking LLM to fix...]][/yellow]")
                new_sparql, _ = llm.fix(question, sparql, error_hint)
                if new_sparql is None:
                    if verbose:
                        console.print("  [yellow][[LLM returned no SPARQL on retry — giving up]][/yellow]")
                    return sparql, set(), attempt
                sparql = new_sparql
                if verbose:
                    console.print("\n  [bold]Corrected SPARQL:[/bold]")
                    console.print(Syntax(sparql, "sparql", theme="monokai"))
            else:
                raise
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"GraphDB request failed — {exc}")


def _match_label(llm_vals: set, expected: set) -> str:
    if llm_vals == expected:
        return "EXACT"
    if not (llm_vals & expected):
        return "NONE"
    return f"PARTIAL ({len(llm_vals & expected)}/{len(expected)} correct)"


def _match_style(label: str) -> str:
    if label == "EXACT":
        return "bold green"
    if label.startswith("PARTIAL"):
        return "bold yellow"
    return "bold red"


def fmt_set(s: set) -> str:
    if not s:
        return "  (no results)"
    return "\n".join(f"  {v}" for v in sorted(s))


def _reference_vals(q: dict) -> set:
    try:
        rows = graphdb.query(q["reference_sparql"])
        return graphdb.extract_values(rows)
    except (requests.exceptions.RequestException, RuntimeError):
        return set()


def run_question_silent(q: dict) -> tuple:
    """Returns (label, had_retry, sparql, llm_vals, ref_vals)."""
    try:
        sparql, _ = llm.ask(q["question"])
    except requests.ConnectionError:
        return "CONNECTION ERROR", False, None, set(), set()
    ref_vals = _reference_vals(q)
    if sparql is None:
        return "EXTRACTION FAILED", False, None, set(), ref_vals
    had_retry = False
    try:
        final_sparql, llm_vals, attempts = _execute_with_retry(q["question"], sparql, verbose=False)
        sparql = final_sparql
        had_retry = attempts > 1
    except (requests.HTTPError, RuntimeError):
        llm_vals = set()
    label = _match_label(llm_vals, ref_vals)
    return label, had_retry, sparql, llm_vals, ref_vals


# ── question / category selection ─────────────────────────────────────────────

def _print_question_list():
    for cat in sorted(qbank.CAT_LABELS):
        console.print(f"\n  [bold cyan]Category {cat} — {qbank.CAT_LABELS[cat]}:[/bold cyan]")
        for q in qbank.QUESTIONS:
            if q["category"] == cat:
                console.print(f"    [bold]{q['number']:2}.[/bold] {q['question']}")


def select_question() -> dict | None:
    _print_question_list()
    try:
        n = int(input("\nQuestion number: ").strip())
    except ValueError:
        console.print("[red]Invalid input.[/red]")
        return None
    matches = [q for q in qbank.QUESTIONS if q["number"] == n]
    if not matches:
        console.print("[red]Invalid question number.[/red]")
        return None
    return matches[0]


def select_category() -> list | None:
    console.print("\n[bold]Categories:[/bold]")
    for cat in sorted(qbank.CAT_LABELS):
        count = sum(1 for q in qbank.QUESTIONS if q["category"] == cat)
        console.print(f"  [bold cyan]{cat}.[/bold cyan] {qbank.CAT_LABELS[cat]} [dim]({count} questions)[/dim]")
    try:
        cat = int(input("Category number: ").strip())
    except ValueError:
        console.print("[red]Invalid input.[/red]")
        return None
    subset = [q for q in qbank.QUESTIONS if q["category"] == cat]
    if not subset:
        console.print(f"[red]No questions in category {cat}.[/red]")
        return None
    return subset


# ── single question (full output) ─────────────────────────────────────────────

def run_test(q: dict, brief_on_exact: bool = False) -> tuple:
    cat = q["category"]
    try:
        sparql, raw = llm.ask(q["question"])
    except requests.ConnectionError:
        console.print("[red]Cannot reach Ollama — is it running on port 11434?[/red]")
        return "CONNECTION ERROR", False

    if sparql is None:
        console.rule(f"[bold cyan]Cat {cat} · {q['question']}[/bold cyan]")
        console.print("\n[bold red]LLM response (no SPARQL block found):[/bold red]")
        console.print(raw, highlight=False)
        console.print("\n[bold]Reference SPARQL:[/bold]")
        console.print(Syntax(q["reference_sparql"], "sparql", theme="monokai"))
        console.print(f"\n[bold]Reference Results:[/bold]\n{fmt_set(_reference_vals(q))}", highlight=False)
        console.print("\n[bold red]Match: EXTRACTION FAILED[/bold red]")
        console.rule()
        return "EXTRACTION FAILED", False

    had_retry = False
    try:
        _, llm_vals, attempts = _execute_with_retry(q["question"], sparql, verbose=not brief_on_exact)
        had_retry = attempts > 1
    except (requests.HTTPError, RuntimeError) as exc:
        if not brief_on_exact:
            console.print(f"\n[red]GraphDB error — {exc}[/red]")
        llm_vals = set()

    ref_vals = _reference_vals(q)
    label = _match_label(llm_vals, ref_vals)
    style = _match_style(label)

    if brief_on_exact and label == "EXACT":
        console.print(f"  [[Cat {cat}]] [bold green]EXACT[/bold green]  — {q['question']}")
        return label, had_retry

    console.rule(f"[bold cyan]Cat {cat} · {q['question']}[/bold cyan]")
    console.print("\n[bold]LLM SPARQL:[/bold]")
    console.print(Syntax(sparql, "sparql", theme="monokai"))
    console.print(f"\n[bold]LLM Results:[/bold]\n{fmt_set(llm_vals)}", highlight=False)
    console.print("\n[bold]Reference SPARQL:[/bold]")
    console.print(Syntax(q["reference_sparql"], "sparql", theme="monokai"))
    console.print(f"\n[bold]Reference Results:[/bold]\n{fmt_set(ref_vals)}", highlight=False)
    console.print(f"\n[bold]Match:[/bold] [{style}]{label}[/{style}]")
    console.rule()
    return label, had_retry


def run_single():
    q = select_question()
    if q:
        run_test(q)


# ── free-form ─────────────────────────────────────────────────────────────────

def run_freeform():
    question = input("Enter your question: ").strip()
    if not question:
        console.print("[red]No question entered.[/red]")
        return
    try:
        sparql, raw = llm.ask(question)
    except requests.ConnectionError:
        console.print("[red]Cannot reach Ollama — is it running on port 11434?[/red]")
        return
    if sparql is None:
        console.print("\n[bold red]LLM response (no SPARQL block found):[/bold red]")
        console.print(raw, highlight=False)
        return
    console.print("\n[bold]LLM SPARQL:[/bold]")
    console.print(Syntax(sparql, "sparql", theme="monokai"))
    try:
        _, vals, _ = _execute_with_retry(question, sparql)
        console.print(f"\n[bold]Results:[/bold]\n{fmt_set(vals)}", highlight=False)
    except (requests.HTTPError, RuntimeError) as exc:
        console.print(f"\n[red]GraphDB error — {exc}[/red]")
