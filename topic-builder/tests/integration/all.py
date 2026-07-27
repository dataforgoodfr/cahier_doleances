"""
Entry point that runs all integration tests in sequence.

Run with:
    python -m tests.integration.all
"""

import sys
import traceback

from tests.integration import discover_topics, factorize, label

TESTS = [discover_topics, factorize, label]


def run() -> None:
    """
    Run every integration test module in sequence, report pass/fail, and exit non-zero on any failure.
    """
    failures = []
    for module in TESTS:
        name = module.__name__.split(".")[-1]
        try:
            module.run()
            print(f"  {name}: PASSED")
        except Exception:
            failures.append(name)
            print(f"  {name}: FAILED")
            traceback.print_exc()

    print(f"\n{len(TESTS) - len(failures)}/{len(TESTS)} passed.")
    if failures:
        sys.exit(1)
    return None


if __name__ == "__main__":
    run()
