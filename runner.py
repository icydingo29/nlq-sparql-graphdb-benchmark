import requests

import graphdb
import llm
import questions as qbank

DIVIDER = "═" * 60
THIN = "─" * 45
MAX_RETRIES = 2


# ── execution helpers ─────────────────────────────────────────────────────────

def _execute_with_retry(question: str, sparql: str, verbose: bool = True) -> tuple:
    attempt = 0
    while True:
        attempt += 1
        try:
            rows = graphdb.query(sparql)
            return sparql, graphdb.extract_values(rows), attempt
        except requests.HTTPError as exc:
            is_syntax_error = exc.response is not None and exc.response.status_code == 400
            if is_syntax_error and attempt <= MAX_RETRIES:
                error_hint = exc.response.text[:300] if (exc.response is not None and exc.response.text) else str(exc)
                if verbose:
                    print(f"\n  [Retry {attempt}/{MAX_RETRIES} — syntax error, asking LLM to fix...]")
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


def fmt_set(s: set) -> str:
    if not s:
        return "  (no results)"
    return "\n".join(f"  {v}" for v in sorted(s))


def _reference_vals(q: dict) -> set:
    try:
        rows = graphdb.query(q["reference_sparql"])
        return graphdb.extract_values(rows)
    except (requests.HTTPError, RuntimeError):
        return set()


def run_question_silent(q: dict) -> tuple:
    """Returns (label, had_retry, sparql, llm_vals, ref_vals)."""
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
    for cat in sorted(qbank.CAT_LABELS):
        print(f"\n  Category {cat} — {qbank.CAT_LABELS[cat]}:")
        for q in qbank.QUESTIONS:
            if q["category"] == cat:
                print(f"    {q['number']:2}. {q['question']}")


def select_question() -> dict | None:
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


def select_category() -> list | None:
    print("\nCategories:")
    for cat in sorted(qbank.CAT_LABELS):
        count = sum(1 for q in qbank.QUESTIONS if q["category"] == cat)
        print(f"  {cat}. {qbank.CAT_LABELS[cat]} ({count} questions)")
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


# ── single question (full output) ─────────────────────────────────────────────

def run_test(q: dict, brief_on_exact: bool = False) -> tuple:
    cat = q["category"]
    sparql, raw = llm.ask(q["question"])

    if sparql is None:
        print(f"\n{DIVIDER}")
        print(f"[Cat {cat}] {q['question']}")
        print(DIVIDER)
        print("\nLLM response (no SPARQL block found):")
        print(raw)
        print(f"\nReference SPARQL:\n{q['reference_sparql']}")
        print(f"\nReference Results:\n{fmt_set(_reference_vals(q))}")
        print("\nMatch: EXTRACTION FAILED")
        print(DIVIDER)
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

    print(f"\n{DIVIDER}")
    print(f"[Cat {cat}] {q['question']}")
    print(DIVIDER)
    print(f"\nLLM SPARQL:\n{sparql}")
    print(f"\nLLM Results:\n{fmt_set(llm_vals)}")
    print(f"\nReference SPARQL:\n{q['reference_sparql']}")
    print(f"\nReference Results:\n{fmt_set(ref_vals)}")
    print(f"\nMatch: {label}")
    print(DIVIDER)
    return label, had_retry


def run_single():
    q = select_question()
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
        print(f"\nResults:\n{fmt_set(vals)}")
    except (requests.HTTPError, RuntimeError) as exc:
        print(f"\nGraphDB error — {exc}")
