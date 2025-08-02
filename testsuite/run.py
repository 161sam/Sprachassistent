"""Simple CLI to run the test suite with profiles and scopes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from base_test import BaseTest


SCOPES = {
    "all": "",
    "backend": "test_backend.py",
    "tts": "test_tts",
    "stt": "test_stt",
    "integrations": "test_integrations",
    "desktop": "test_desktop",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run testsuite")
    parser.add_argument("--profile", help="Environment profile", default=None)
    parser.add_argument("--scope", choices=SCOPES.keys(), default="all")
    parser.add_argument("--report", choices=["junit"], default=None)
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.profile:
        BaseTest.load_env(profile=args.profile)
    else:
        BaseTest.load_env()

    pytest_args = ["testsuite"]
    if args.scope != "all":
        path = SCOPES[args.scope]
        pytest_args = [f"testsuite/{path}"] if path else ["testsuite"]
    if args.fail_fast:
        pytest_args.append("-x")
    if args.report == "junit":
        Path("reports").mkdir(exist_ok=True)
        pytest_args += ["--junitxml", "reports/junit.xml"]

    return pytest.main(pytest_args)


if __name__ == "__main__":
    sys.exit(main())
