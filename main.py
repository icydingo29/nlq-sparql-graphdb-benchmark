import sys

import config
from benchmark import run_benchmark
from runner import run_single, run_freeform


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
