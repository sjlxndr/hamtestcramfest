#!/usr/bin/env python3
"""
Derive answerkey.txt from the Technician Pool.

Usage:
    python3 make_answerkey.py --out answerkey.txt
    python3 make_answerkey.py          # prompts, offering the defaults below

Every answer in the pool sits on a line of its own, as

    <question ID> (<answer letter>)[ [<code reference>]]

so one regex over the pool text yields the whole key. The code reference
is matched only so it cannot leak into the output; it is discarded.

Output is "<question ID> <answer letter>" per line, in pool order, which
is the format run_quiz.py and score_quiz.py read.
"""
import re
import os
import sys
import argparse

from extract_questions import POOL_FILE, pool_text

ANSWERKEY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "answerkey.txt"
)

ANSWER_LINE = re.compile(
    r'^(T[0-9][A-Z][0-9]{2})\s+\(([A-D])\)(?:\s*\[([^\]]+)\])?\s*$',
    re.M,
)


def build_answerkey(path):
    text = pool_text(path)
    text = text.replace("\f", "")  # strip page-break artifacts
    return [(qid, ans) for qid, ans, _ref in ANSWER_LINE.findall(text)]


def prompt(label, default=None):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default


def parse_args():
    parser = argparse.ArgumentParser(
        description="Derive the Technician Pool answer key from the pool.",
    )
    parser.add_argument("--pool", default=POOL_FILE, help="pool PDF or text dump")
    parser.add_argument("--out", default=ANSWERKEY_FILE, help="answer key to write")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        args.pool = prompt("Question pool file", POOL_FILE)
        args.out = prompt("Answer key file", ANSWERKEY_FILE)
    return args


def main():
    args = parse_args()

    key = build_answerkey(args.pool)

    with open(args.out, "w") as f:
        for qid, ans in key:
            f.write(f"{qid} {ans}\n")

    print(f"Wrote {len(key)} answer(s) to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
