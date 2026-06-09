import sys
import requests
from collections import defaultdict

import config
import graphdb
import llm
import questions as qbank

_DIVIDER = "═" * 60
_THIN = "─" * 45

_MAX_RETRIES = 2

_CAT_LABELS = {
    1: "Direct",
    2: "Transitivity",
    3: "Defined class",
    4: "Reasoning",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _execute_with_retry(question: str, sparql: str, verbose: bool = True) -> tuple:
    """Execute SPARQL against GraphDB, retrying up to _MAX_RETRIES times on syntax errors (HTTP 400).
    Returns (final_sparql, result_set, total_attempts). Raises on non-400 errors."""
    attempt = 0
    while True:
        attempt += 1
        try:
            rows = graphdb.query(sparql)
            return sparql, graphdb.extract_values(rows), attempt
        except requests.HTTPError as exc:
            is_syntax_error = exc.response is not None and exc.response.status_code == 400
            if is_syntax_error and attempt <= _MAX_RETRIES:
                error_hint = exc.response.text[:300] if (exc.response is not None and exc.response.text) else str(exc)
                if verbose:
                    print(f"\n  [Retry {attempt}/{_MAX_RETRIES} — syntax error, asking LLM to fix...]")
                new_sparql, _ = llm.fix(question, sparql, error_hint)
                if new_sparql is None:
                    if verbose:
                        print("  [LLM returned no SPARQL on retry — giving up]")
                    return sparql, set(), attempt
                sparql = new_sparql
                if verbose:
                    print(f"\n  Corrected SPARQL:\n{sparql}")
            else:
                raise


def _match_label(llm_vals: set, expected: set) -> str:
    if llm_vals == expected:
        return "EXACT"
    inter = llm_vals & expected
    if not inter:
        return "NONE"
    return f"PARTIAL ({len(inter)}/{len(expected)} correct)"


def _fmt_set(s: set) -> str:
    if not s:
        return "  (no results)"
    return "\n".join(f"  {v}" for v in sorted(s))


def _reference_vals(q: dict) -> set:
    """Execute the reference SPARQL and return its result set."""
    try:
        rows = graphdb.query(q["reference_sparql"])
        return graphdb.extract_values(rows)
    except (requests.HTTPError, RuntimeError):
        return set()


def _run_question_silent(q: dict) -> tuple:
    """Execute one question with no output. Returns (label, had_retry)."""
    sparql, _ = llm.ask(q["question"])
    if sparql is None:
        return "EXTRACTION FAILED", False
    had_retry = False
    try:
        _, llm_vals, attempts = _execute_with_retry(q["question"], sparql, verbose=False)
        had_retry = attempts > 1
    except (requests.HTTPError, RuntimeError):
        llm_vals = set()
    return _match_label(llm_vals, _reference_vals(q)), had_retry


def _print_summary(cat_scores: dict, total_exact: int, syntax_retries: int):
    print(f"\nSUMMARY")
    print(_THIN)
    for cat in sorted(cat_scores):
        right, total = cat_scores[cat]
        label = _CAT_LABELS.get(cat, f"Cat {cat}")
        print(f"  Category {cat} ({label}):".ljust(34) + f"{right} / {total}")
    print(_THIN)
    all_total = sum(v[1] for v in cat_scores.values())
    print(f"  {'Total:'.ljust(32)} {total_exact} / {all_total}")
    print(f"  {'Syntax retries:'.ljust(32)} {syntax_retries}")


# ── run a single test question ────────────────────────────────────────────────

def run_test(q: dict, brief_on_exact: bool = False) -> tuple:
    """Run one test question with full output. Returns (match_label, had_syntax_retry).
    If brief_on_exact=True, prints a single line for EXACT results instead of the full block."""
    cat = q["category"]

    sparql, raw = llm.ask(q["question"])

    if sparql is None:
        print(f"\n{_DIVIDER}")
        print(f"[Cat {cat}] {q['question']}")
        print(_DIVIDER)
        print("\nLLM response (no SPARQL block found):")
        print(raw)
        print("\nNo SPARQL query could be extracted.")
        print(f"\nReference SPARQL:\n{q['reference_sparql']}")
        print(f"\nReference Results:\n{_fmt_set(q['expected_results'])}")
        print(f"\nMatch: EXTRACTION FAILED")
        print(_DIVIDER)
        return "EXTRACTION FAILED", False

    had_retry = False
    try:
        _, llm_vals, attempts = _execute_with_retry(q["question"], sparql, verbose=not brief_on_exact)
        had_retry = attempts > 1
    except (requests.HTTPError, RuntimeError) as exc:
        if not brief_on_exact:
            print(f"\nLLM Results: GraphDB error — {exc}")
        llm_vals = set()

    ref_vals = _reference_vals(q)
    label = _match_label(llm_vals, ref_vals)

    if brief_on_exact and label == "EXACT":
        print(f"  [Cat {cat}] EXACT  — {q['question']}")
        return label, had_retry

    print(f"\n{_DIVIDER}")
    print(f"[Cat {cat}] {q['question']}")
    print(_DIVIDER)
    print(f"\nLLM SPARQL:\n{sparql}")
    print(f"\nLLM Results:")
    print(_fmt_set(llm_vals))
    print(f"\nReference SPARQL:\n{q['reference_sparql']}")
    print(f"\nReference Results:")
    print(_fmt_set(ref_vals))
    print(f"\nMatch: {label}")
    print(_DIVIDER)
    return label, had_retry


# ── run-all ──────────────────────────────────────────────────────────────────

def run_all():
    cat_scores = defaultdict(lambda: [0, 0])
    total_exact = 0
    syntax_retries = 0

    for q in qbank.QUESTIONS:
        label, had_retry = run_test(q)
        cat = q["category"]
        cat_scores[cat][1] += 1
        if label == "EXACT":
            cat_scores[cat][0] += 1
            total_exact += 1
        if had_retry:
            syntax_retries += 1

    _print_summary(cat_scores, total_exact, syntax_retries)


# ── show failures only ────────────────────────────────────────────────────────

def run_failures_only():
    cat_scores = defaultdict(lambda: [0, 0])
    total_exact = 0
    syntax_retries = 0

    for q in qbank.QUESTIONS:
        label, had_retry = run_test(q, brief_on_exact=True)
        cat = q["category"]
        cat_scores[cat][1] += 1
        if label == "EXACT":
            cat_scores[cat][0] += 1
            total_exact += 1
        if had_retry:
            syntax_retries += 1

    _print_summary(cat_scores, total_exact, syntax_retries)


# ── benchmark (N silent runs) ─────────────────────────────────────────────────

def run_benchmark():
    try:
        n = int(input("Number of runs (default 5): ").strip() or "5")
        if n < 1:
            raise ValueError
    except ValueError:
        print("Invalid number.")
        return

    n_questions = len(qbank.QUESTIONS)
    exact_counts = [0] * n_questions
    total_retries = 0

    for run_idx in range(1, n + 1):
        print(f"\nRun {run_idx}/{n}...", end=" ", flush=True)
        run_exact = 0
        for qi, q in enumerate(qbank.QUESTIONS):
            label, had_retry = _run_question_silent(q)
            if label == "EXACT":
                exact_counts[qi] += 1
                run_exact += 1
            if had_retry:
                total_retries += 1
        print(f"{run_exact}/{n_questions} exact")

    print(f"\nBENCHMARK RESULTS ({n} runs)")
    print(_THIN)

    cat_totals = defaultdict(lambda: [0, 0])
    for qi, q in enumerate(qbank.QUESTIONS):
        cat = q["category"]
        cat_totals[cat][0] += exact_counts[qi]
        cat_totals[cat][1] += n

    for cat in sorted(cat_totals):
        right_sum, total = cat_totals[cat]
        label = _CAT_LABELS.get(cat, f"Cat {cat}")
        print(f"  Category {cat} ({label}):".ljust(34) + f"{right_sum / total * 100:.0f}%  ({right_sum}/{total})")

    print(_THIN)
    total_right = sum(exact_counts)
    grand_total = n_questions * n
    print(f"  {'Overall:'.ljust(32)} {total_right / grand_total * 100:.0f}%  ({total_right}/{grand_total})")
    print(f"  {'Syntax retries:'.ljust(32)} {total_retries}")

    print(f"\nPer-question exact rate:")
    for qi, q in enumerate(qbank.QUESTIONS):
        pct = exact_counts[qi] / n * 100
        bar = "█" * exact_counts[qi] + "░" * (n - exact_counts[qi])
        print(f"  Q{qi+1:2} [{bar}] {pct:3.0f}%  {q['question'][:45]}")


# ── free-form ─────────────────────────────────────────────────────────────────

def run_freeform():
    question = input("Enter your question: ").strip()
    if not question:
        print("No question entered.")
        return

    sparql, raw = llm.ask(question)

    if sparql is None:
        print("\nLLM response (no SPARQL block found):")
        print(raw)
        print("\nNo SPARQL query could be extracted.")
        return

    print(f"\nLLM SPARQL:\n{sparql}")

    try:
        _, vals, _ = _execute_with_retry(question, sparql)
        print(f"\nResults:")
        print(_fmt_set(vals))
    except (requests.HTTPError, RuntimeError) as exc:
        print(f"\nResults: GraphDB error — {exc}")


# ── menu ──────────────────────────────────────────────────────────────────────

def print_menu():
    print("\nGeographic Ontology NLQ Tester")
    print("=" * 34)
    for i, q in enumerate(qbank.QUESTIONS, 1):
        print(f"  {i:2}. [Cat {q['category']}] {q['question']}")
    print(f"   A.  Run all (full output)")
    print(f"   S.  Run all (failures only)")
    print(f"   B.  Benchmark (N runs, averages)")
    print(f"   F.  Free-form question")
    print(f"   Q.  Quit")
    print()


def main():
    print(f"Using model : {config.OLLAMA_MODEL}")
    print(f"GraphDB     : {config.GRAPHDB_ENDPOINT}")

    while True:
        print_menu()
        choice = input("Select: ").strip().upper()

        if choice == "Q":
            print("Goodbye.")
            sys.exit(0)
        elif choice == "A":
            run_all()
        elif choice == "S":
            run_failures_only()
        elif choice == "B":
            run_benchmark()
        elif choice == "F":
            run_freeform()
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(qbank.QUESTIONS):
                    run_test(qbank.QUESTIONS[idx])
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid selection.")


if __name__ == "__main__":
    main()
