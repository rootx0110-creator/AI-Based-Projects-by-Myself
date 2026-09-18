"""Simulates the interactive menu flow to reproduce user-reported bugs."""
import builtins
import sys

import port_scanner as p

# args passed to harness: answers for target, port-choice, scan-choice, detect
ANSWERS = sys.argv[1:] or ["127.0.0.1", "1", "1", "y"]


def fake_input(prompt=""):
    a = ANSWERS.pop(0) if ANSWERS else ""
    sys.stdout.write(f"PROMPT>{prompt}{a}\n")
    return a


builtins.input = fake_input
sys.stdin.isatty = lambda: True

rc = p.run(p.build_parser().parse_args([]))
print(f"\n=== exit code: {rc} ===")
