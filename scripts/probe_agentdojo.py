"""Probe AgentDojo suites without calling an LLM API.

This script assumes AgentDojo is installed in the active environment. It is
used for setup and oracle sanity checks before running expensive model-based
benchmarks.
"""

from __future__ import annotations

import argparse

from agentdojo.task_suite.load_suites import get_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe AgentDojo suite metadata")
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    suite = get_suite(args.benchmark_version, args.suite)
    print(
        f"{args.suite} user_tasks={len(suite.user_tasks)} "
        f"injection_tasks={len(suite.injection_tasks)} tools={len(suite.tools)}"
    )

    if args.check:
        passed, (user_results, injection_results) = suite.check(check_injectable=False)
        print("passed", passed)
        print(
            "user_tasks",
            len(user_results),
            "user_failures",
            sum(1 for ok, _ in user_results.values() if not ok),
        )
        print(
            "injection_tasks",
            len(injection_results),
            "injection_failures",
            sum(1 for ok in injection_results.values() if not ok),
        )
        for task_id, (ok, reason) in user_results.items():
            if not ok:
                print("USER_FAIL", task_id, reason)
        for task_id, ok in injection_results.items():
            if not ok:
                print("INJECTION_FAIL", task_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
