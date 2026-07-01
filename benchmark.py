from collections import defaultdict

import reference_questions as qbank
from runner import DIVIDER, THIN, fmt_set, run_question_silent, select_question, select_category


def _print_benchmark_stats(questions: list, exact_counts: list, n: int, total_retries: int):
    print(f"\nBENCHMARK RESULTS ({n} runs)")
    print(THIN)

    cat_totals = defaultdict(lambda: [0, 0])
    for qi, q in enumerate(questions):
        cat_totals[q["category"]][0] += exact_counts[qi]
        cat_totals[q["category"]][1] += n

    for cat in sorted(cat_totals):
        right, total = cat_totals[cat]
        print(f"  Category {cat} ({qbank.CAT_LABELS.get(cat, f'Cat {cat}')}):".ljust(34)
              + f"{right / total * 100:.0f}%  ({right}/{total})")

    print(THIN)
    total_right = sum(exact_counts)
    grand_total = len(questions) * n
    print(f"  {'Overall:'.ljust(32)} {total_right / grand_total * 100:.0f}%  ({total_right}/{grand_total})")
    print(f"  {'Syntax retries:'.ljust(32)} {total_retries}")

    print("\nPer-question exact rate:")
    for cat in sorted({q["category"] for q in questions}):
        print(f"\n  Category {cat} — {qbank.CAT_LABELS[cat]}:")
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
    failure_patterns: dict[int, dict] = {}

    for run_idx in range(1, n + 1):
        if out == "V":
            print(f"\nRun {run_idx}/{n}")
        else:
            print(f"\nRun {run_idx}/{n}...", end=" ", flush=True)

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
        print(f"\n{THIN}")
        print("FAILURE PATTERNS PER QUESTION")
        for qi, q in enumerate(questions):
            if qi not in failure_patterns:
                continue
            rate = exact_counts[qi] / n * 100
            n_fails = n - exact_counts[qi]
            patterns = sorted(failure_patterns[qi].items(), key=lambda x: x[1][0], reverse=True)
            ref_vals = patterns[0][1][2]

            print(f"\n{DIVIDER}")
            print(f"[Cat {q['category']}] Q{q['number']} — {q['question']}")
            print(f"  {rate:.0f}% exact  |  {n_fails} failure(s)  |  {len(patterns)} unique pattern(s)")
            print(DIVIDER)

            for i, (sparql, (count, llm_vals, _)) in enumerate(patterns, 1):
                print(f"\n  Pattern {i}  ×{count}:")
                print("\n  LLM SPARQL:")
                for line in sparql.splitlines():
                    print(f"    {line}")
                print(f"\n  LLM Results:\n{fmt_set(llm_vals)}")

            print(f"\n  Reference Results:\n{fmt_set(ref_vals)}")
            print(DIVIDER)
