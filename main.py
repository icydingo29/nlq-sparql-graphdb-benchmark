import sys
import requests

import config
import graphdb
import llm
import questions as qbank

_DIVIDER = "═" * 60
_THIN = "─" * 45

_CAT_LABELS = {
    1: "Direct",
    2: "Transitivity",
    3: "Defined class",
    4: "Reasoning",
}


# ── helpers ──────────────────────────────────────────────────────────────────

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


def _fmt_rows(rows: list) -> str:
    if not rows:
        return "  (no results)"
    lines = []
    for row in rows:
        lines.append("  " + "  |  ".join(f"{k}: {v}" for k, v in row.items()))
    return "\n".join(lines)


# ── run a single test question ────────────────────────────────────────────────

def run_test(q: dict) -> str:
    """Run one test question; return match label."""
    cat = q["category"]
    print(f"\n{_DIVIDER}")
    print(f"[Cat {cat}] {q['question']}")
    print(_DIVIDER)

    sparql, raw = llm.ask(q["question"])

    if sparql is None:
        print("\nLLM response (no SPARQL block found):")
        print(raw)
        print("\nNo SPARQL query could be extracted.")
        print(f"\nReference SPARQL:\n{q['reference_sparql']}")
        print(f"\nReference Results:\n{_fmt_set(q['expected_results'])}")
        print(f"\nMatch: EXTRACTION FAILED")
        print(_DIVIDER)
        return "EXTRACTION FAILED"

    print(f"\nLLM SPARQL:\n{sparql}")

    try:
        llm_rows = graphdb.query(sparql)
        llm_vals = graphdb.extract_values(llm_rows)
        print(f"\nLLM Results:")
        print(_fmt_set(llm_vals))
    except (requests.HTTPError, RuntimeError) as exc:
        print(f"\nLLM Results: GraphDB error — {exc}")
        llm_vals = set()

    print(f"\nReference SPARQL:\n{q['reference_sparql']}")
    print(f"\nReference Results:\n{_fmt_set(q['expected_results'])}")

    label = _match_label(llm_vals, q["expected_results"])
    print(f"\nMatch: {label}")
    print(_DIVIDER)
    return label


# ── run-all ──────────────────────────────────────────────────────────────────

def run_all():
    from collections import defaultdict
    cat_scores = defaultdict(lambda: [0, 0])  # [exact_or_partial, total]
    total_exact = 0

    for q in qbank.QUESTIONS:
        label = run_test(q)
        cat = q["category"]
        cat_scores[cat][1] += 1
        if label == "EXACT":
            cat_scores[cat][0] += 1
            total_exact += 1

    print(f"\nSUMMARY")
    print(_THIN)
    for cat in sorted(cat_scores):
        right, total = cat_scores[cat]
        label = _CAT_LABELS.get(cat, f"Cat {cat}")
        print(f"  Category {cat} ({label}):".ljust(34) + f"{right} / {total}")
    print(_THIN)
    all_total = sum(v[1] for v in cat_scores.values())
    print(f"  {'Total:'.ljust(32)} {total_exact} / {all_total}")


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
        rows = graphdb.query(sparql)
        print(f"\nResults:")
        if rows:
            print(_fmt_rows(rows))
            vals = graphdb.extract_values(rows)
            print(f"  → {len(rows)} row(s); values: {sorted(vals)}")
        else:
            print("  (no results)")
            print("  Note: query executed but returned zero rows.")
            print(f"  Generated query shown above for inspection.")
    except (requests.HTTPError, RuntimeError) as exc:
        print(f"\nResults: GraphDB error — {exc}")


# ── menu ──────────────────────────────────────────────────────────────────────

def print_menu():
    print("\nGeographic Ontology NLQ Tester")
    print("=" * 34)
    for i, q in enumerate(qbank.QUESTIONS, 1):
        print(f"  {i:2}. [Cat {q['category']}] {q['question']}")
    print(f"   A.  Run all test questions")
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
