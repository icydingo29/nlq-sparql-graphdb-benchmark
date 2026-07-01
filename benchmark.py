from collections import defaultdict

from rich.syntax import Syntax
from rich.table import Table
from rich import box

import reference_questions as qbank
from runner import console, fmt_set, run_question_silent, select_question, select_category


def _pct_style(pct: float) -> str:
    if pct >= 80:
        return "green"
    if pct >= 50:
        return "yellow"
    return "red"


def _print_benchmark_stats(questions: list, exact_counts: list, n: int, total_retries: int):
    cat_totals = defaultdict(lambda: [0, 0])
    for qi, q in enumerate(questions):
        cat_totals[q["category"]][0] += exact_counts[qi]
        cat_totals[q["category"]][1] += n

    total_right = sum(exact_counts)
    grand_total = len(questions) * n
    overall_pct = total_right / grand_total * 100

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan", title=f"Benchmark Results ({n} runs)")
    table.add_column("Category", style="cyan")
    table.add_column("Accuracy", justify="right")
    table.add_column("Score", justify="right")

    for cat in sorted(cat_totals):
        right, total = cat_totals[cat]
        pct = right / total * 100
        style = _pct_style(pct)
        table.add_row(
            f"{cat}  {qbank.CAT_LABELS.get(cat, f'Cat {cat}')}",
            f"[{style}]{pct:.0f}%[/{style}]",
            f"{right}/{total}",
        )

    table.add_section()
    o_style = _pct_style(overall_pct)
    table.add_row(
        "[bold]Overall[/bold]",
        f"[bold {o_style}]{overall_pct:.0f}%[/bold {o_style}]",
        f"[bold]{total_right}/{grand_total}[/bold]",
    )

    console.print()
    console.print(table)
    console.print(f"  [dim]Syntax retries:[/dim] {total_retries}")

    console.print("\n[bold]Per-question exact rate:[/bold]")
    for cat in sorted({q["category"] for q in questions}):
        console.print(f"\n  [bold cyan]Category {cat} — {qbank.CAT_LABELS[cat]}:[/bold cyan]")
        for qi, q in enumerate(questions):
            if q["category"] != cat:
                continue
            pct = exact_counts[qi] / n * 100
            style = _pct_style(pct)
            filled = "█" * exact_counts[qi]
            empty = "░" * (n - exact_counts[qi])
            console.print(
                f"    Q{q['number']:2} [{style}]{filled}[/{style}][dim]{empty}[/dim]"
                f" [{style}]{pct:3.0f}%[/{style}]  {q['question'][:45]}"
            )


def run_benchmark():
    # ── scope ────────────────────────────────────────────────────────────────
    console.print("\n[bold]Benchmark scope:[/bold]")
    console.print("  [bold cyan]S[/bold cyan]  Single question")
    console.print("  [bold cyan]C[/bold cyan]  Category")
    console.print("  [bold cyan]A[/bold cyan]  All questions")
    scope = input("Scope [S/C/A]: ").strip().upper()

    if scope == "S":
        q = select_question()
        if q is None:
            return
        questions = [q]
    elif scope == "C":
        questions = select_category()
        if questions is None:
            return
    elif scope == "A":
        questions = list(qbank.QUESTIONS)
    else:
        console.print("[red]Invalid scope.[/red]")
        return

    # ── runs ─────────────────────────────────────────────────────────────────
    try:
        n = int(input("Runs (default 10): ").strip() or "10")
        if n < 1:
            raise ValueError
    except ValueError:
        console.print("[red]Invalid number.[/red]")
        return

    # ── output mode ──────────────────────────────────────────────────────────
    console.print("Output:  [bold cyan]P[/bold cyan]  progress only [dim](default)[/dim]")
    console.print("         [bold cyan]F[/bold cyan]  show all unique failure patterns per question after stats")
    console.print("         [bold cyan]V[/bold cyan]  one result line per question per run")
    out = input("Output [P/F/V]: ").strip().upper() or "P"
    if out not in ("P", "F", "V"):
        out = "P"

    # ── run ───────────────────────────────────────────────────────────────────
    n_questions = len(questions)
    exact_counts = [0] * n_questions
    total_retries = 0
    failure_patterns: dict[int, dict] = {}

    for run_idx in range(1, n + 1):
        if out == "V":
            console.print(f"\n[bold]Run {run_idx}/{n}[/bold]")
        else:
            console.print(f"\n[dim]Run {run_idx}/{n}...[/dim] ", end="")

        run_exact = 0
        for qi, q in enumerate(questions):
            label, had_retry, sparql, llm_vals, ref_vals = run_question_silent(q)

            if label == "EXACT":
                exact_counts[qi] += 1
                run_exact += 1
            else:
                key = sparql if sparql is not None else "(extraction failed)"
                entry = failure_patterns.setdefault(qi, {})
                if key not in entry:
                    entry[key] = [0, llm_vals, ref_vals]
                entry[key][0] += 1

            if had_retry:
                total_retries += 1

            if out == "V":
                style = "green" if label == "EXACT" else ("yellow" if label.startswith("PARTIAL") else "red")
                console.print(f"  Q{q['number']:2}  [{style}]{label:<34}[/{style}]  {q['question'][:38]}")

        exact_style = _pct_style(run_exact / n_questions * 100)
        if out == "V":
            console.print(f"  → [{exact_style}]{run_exact}/{n_questions} exact[/{exact_style}]")
        else:
            console.print(f"[{exact_style}]{run_exact}/{n_questions} exact[/{exact_style}]")

    # ── stats ─────────────────────────────────────────────────────────────────
    _print_benchmark_stats(questions, exact_counts, n, total_retries)

    # ── failure details (F mode) ──────────────────────────────────────────────
    if out == "F" and failure_patterns:
        console.rule("[bold]Failure Patterns[/bold]")
        for qi, q in enumerate(questions):
            if qi not in failure_patterns:
                continue
            rate = exact_counts[qi] / n * 100
            n_fails = n - exact_counts[qi]
            patterns = sorted(failure_patterns[qi].items(), key=lambda x: x[1][0], reverse=True)
            ref_vals = patterns[0][1][2]

            style = _pct_style(rate)
            console.rule(f"[bold cyan]Cat {q['category']} · Q{q['number']} · {q['question']}[/bold cyan]")
            console.print(
                f"  [{style}]{rate:.0f}% exact[/{style}]"
                f"  [dim]|[/dim]  {n_fails} failure(s)"
                f"  [dim]|[/dim]  {len(patterns)} unique pattern(s)"
            )

            for i, (sparql, (count, llm_vals, _)) in enumerate(patterns, 1):
                console.print(f"\n  [bold]Pattern {i}[/bold]  [dim]×{count}[/dim]")
                console.print("\n  [bold]LLM SPARQL:[/bold]")
                console.print(Syntax(sparql, "sparql", theme="monokai"))
                console.print(f"\n  [bold]LLM Results:[/bold]\n{fmt_set(llm_vals)}", highlight=False)

            console.print(f"\n  [bold]Reference Results:[/bold]\n{fmt_set(ref_vals)}", highlight=False)
            console.rule()
