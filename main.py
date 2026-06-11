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
    1: "Direct Retrieval",
    2: "Transitivity",
    3: "Numeric Filter",
    4: "Defined Class",
    5: "Aggregation",
    6: "Compositional",
    7: "Reasoning Required",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _execute_with_retry(question: str, sparql: str, verbose: bool = True) -> tuple:
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
    if not (llm_vals & expected):
        return "NONE"
    return f"PARTIAL ({len(llm_vals & expected)}/{len(expected)} correct)"


def _fmt_set(s: set) -> str:
    if not s:
        return "  (no results)"
    return "\n".join(f"  {v}" for v in sorted(s))


def _reference_vals(q: dict) -> set:
    try:
        rows = graphdb.query(q["reference_sparql"])
        return graphdb.extract_values(rows)
    except (requests.HTTPError, RuntimeError):
        return set()


def _run_question_silent(q: dict) -> tuple:
    """Run one question silently. Returns (label, had_retry, sparql, llm_vals, ref_vals)."""
    sparql, _ = llm.ask(q["question"])
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
    for cat in sorted(_CAT_LABELS):
        print(f"\n  Category {cat} — {_CAT_LABELS[cat]}:")
        for q in qbank.QUESTIONS:
            if q["category"] == cat:
                print(f"    {q['number']:2}. {q['question']}")


def _select_question() -> dict | None:
    _print_question_list()
    try:
        n = int(input("\nQuestion number: ").strip())
    except ValueError:
        print("Invalid input.")
        return None
    matches = [q for q in qbank.QUESTIONS if q["number"] == n]
    if not matches:
        print("Invalid question number.")
        return None
    return matches[0]


def _select_category() -> list | None:
    print("\nCategories:")
    for cat in sorted(_CAT_LABELS):
        count = sum(1 for q in qbank.QUESTIONS if q["category"] == cat)
        print(f"  {cat}. {_CAT_LABELS[cat]} ({count} questions)")
    try:
        cat = int(input("Category number: ").strip())
    except ValueError:
        print("Invalid input.")
        return None
    subset = [q for q in qbank.QUESTIONS if q["category"] == cat]
    if not subset:
        print(f"No questions in category {cat}.")
        return None
    return subset


# ── run single question (full output) ─────────────────────────────────────────

def run_test(q: dict, brief_on_exact: bool = False) -> tuple:
    cat = q["category"]
    sparql, raw = llm.ask(q["question"])

    if sparql is None:
        print(f"\n{_DIVIDER}")
        print(f"[Cat {cat}] {q['question']}")
        print(_DIVIDER)
        print("\nLLM response (no SPARQL block found):")
        print(raw)
        print(f"\nReference SPARQL:\n{q['reference_sparql']}")
        print(f"\nReference Results:\n{_fmt_set(_reference_vals(q))}")
        print(f"\nMatch: EXTRACTION FAILED")
        print(_DIVIDER)
        return "EXTRACTION FAILED", False

    had_retry = False
    try:
        _, llm_vals, attempts = _execute_with_retry(q["question"], sparql, verbose=not brief_on_exact)
        had_retry = attempts > 1
    except (requests.HTTPError, RuntimeError) as exc:
        if not brief_on_exact:
            print(f"\nGraphDB error — {exc}")
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
    print(f"\nLLM Results:\n{_fmt_set(llm_vals)}")
    print(f"\nReference SPARQL:\n{q['reference_sparql']}")
    print(f"\nReference Results:\n{_fmt_set(ref_vals)}")
    print(f"\nMatch: {label}")
    print(_DIVIDER)
    return label, had_retry


def run_single():
    q = _select_question()
    if q:
        run_test(q)


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
        return
    print(f"\nLLM SPARQL:\n{sparql}")
    try:
        _, vals, _ = _execute_with_retry(question, sparql)
        print(f"\nResults:\n{_fmt_set(vals)}")
    except (requests.HTTPError, RuntimeError) as exc:
        print(f"\nGraphDB error — {exc}")


# ── benchmark ─────────────────────────────────────────────────────────────────

def _print_benchmark_stats(questions: list, exact_counts: list, n: int, total_retries: int):
    print(f"\nBENCHMARK RESULTS ({n} runs)")
    print(_THIN)

    cat_totals = defaultdict(lambda: [0, 0])
    for qi, q in enumerate(questions):
        cat_totals[q["category"]][0] += exact_counts[qi]
        cat_totals[q["category"]][1] += n

    for cat in sorted(cat_totals):
        right, total = cat_totals[cat]
        print(f"  Category {cat} ({_CAT_LABELS.get(cat, f'Cat {cat}')}):".ljust(34)
              + f"{right / total * 100:.0f}%  ({right}/{total})")

    print(_THIN)
    total_right = sum(exact_counts)
    grand_total = len(questions) * n
    print(f"  {'Overall:'.ljust(32)} {total_right / grand_total * 100:.0f}%  ({total_right}/{grand_total})")
    print(f"  {'Syntax retries:'.ljust(32)} {total_retries}")

    print(f"\nPer-question exact rate:")
    for cat in sorted({q["category"] for q in questions}):
        print(f"\n  Category {cat} — {_CAT_LABELS[cat]}:")
        for qi, q in enumerate(questions):
            if q["category"] != cat:
                continue
            pct = exact_counts[qi] / n * 100
            bar = "█" * exact_counts[qi] + "░" * (n - exact_counts[qi])
            print(f"    Q{q['number']:2} [{bar}] {pct:3.0f}%  {q['question'][:45]}")


def run_benchmark():
    # ── scope ────────────────────────────────────────────────────────────────
    print("\nBenchmark scope:")
    print("  S  Single question")
    print("  C  Category")
    print("  A  All questions")
    scope = input("Scope [S/C/A]: ").strip().upper()

    if scope == "S":
        q = _select_question()
        if q is None:
            return
        questions = [q]
    elif scope == "C":
        questions = _select_category()
        if questions is None:
            return
    elif scope == "A":
        questions = list(qbank.QUESTIONS)
    else:
        print("Invalid scope.")
        return

    # ── runs ─────────────────────────────────────────────────────────────────
    try:
        n = int(input("Runs (default 10): ").strip() or "10")
        if n < 1:
            raise ValueError
    except ValueError:
        print("Invalid number.")
        return

    # ── output mode ──────────────────────────────────────────────────────────
    print("Output:  P  progress only (default)")
    print("         F  show all unique failure patterns per question after stats")
    print("         V  one result line per question per run")
    out = input("Output [P/F/V]: ").strip().upper() or "P"
    if out not in ("P", "F", "V"):
        out = "P"

    # ── run ───────────────────────────────────────────────────────────────────
    n_questions = len(questions)
    exact_counts = [0] * n_questions
    total_retries = 0
    # qi → {sparql_str: [count, llm_vals, ref_vals]}
    failure_patterns: dict[int, dict] = {}

    for run_idx in range(1, n + 1):
        if out == "V":
            print(f"\nRun {run_idx}/{n}")
        else:
            print(f"\nRun {run_idx}/{n}...", end=" ", flush=True)

        run_exact = 0
        for qi, q in enumerate(questions):
            label, had_retry, sparql, llm_vals, ref_vals = _run_question_silent(q)

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
                tag = "EXACT" if label == "EXACT" else label
                print(f"  Q{q['number']:2}  {tag:<34}  {q['question'][:38]}")

        if out == "V":
            print(f"  → {run_exact}/{n_questions} exact")
        else:
            print(f"{run_exact}/{n_questions} exact")

    # ── stats ─────────────────────────────────────────────────────────────────
    _print_benchmark_stats(questions, exact_counts, n, total_retries)

    # ── failure details (F mode) ──────────────────────────────────────────────
    if out == "F" and failure_patterns:
        print(f"\n{_THIN}")
        print("FAILURE PATTERNS PER QUESTION")
        for qi, q in enumerate(questions):
            if qi not in failure_patterns:
                continue
            rate = exact_counts[qi] / n * 100
            n_fails = n - exact_counts[qi]
            patterns = sorted(failure_patterns[qi].items(), key=lambda x: x[1][0], reverse=True)
            ref_vals = patterns[0][1][2]

            print(f"\n{_DIVIDER}")
            print(f"[Cat {q['category']}] Q{q['number']} — {q['question']}")
            print(f"  {rate:.0f}% exact  |  {n_fails} failure(s)  |  {len(patterns)} unique pattern(s)")
            print(_DIVIDER)

            for i, (sparql, (count, llm_vals, _)) in enumerate(patterns, 1):
                print(f"\n  Pattern {i}  ×{count}:")
                print(f"\n  LLM SPARQL:")
                for line in sparql.splitlines():
                    print(f"    {line}")
                print(f"\n  LLM Results:\n{_fmt_set(llm_vals)}")

            print(f"\n  Reference Results:\n{_fmt_set(ref_vals)}")
            print(_DIVIDER)


# ── menu ──────────────────────────────────────────────────────────────────────

def print_menu():
    print("\nGeographic Ontology NLQ Tester")
    print("=" * 34)
    print("  S  Single question")
    print("  F  Free-form question")
    print("  B  Benchmark")
    print("  Q  Quit")
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
        elif choice == "S":
            run_single()
        elif choice == "F":
            run_freeform()
        elif choice == "B":
            run_benchmark()
        else:
            print("Invalid selection.")


if __name__ == "__main__":
    main()
