#!/usr/bin/env python3
"""
Ham radio license exam practice, driven by an FCC question pool.

Usage:
    python3 cramfest.py --pool pool.pdf
    python3 cramfest.py --pool pool.pdf --score answers_2026-08-11_120000.txt
    python3 cramfest.py                     # prompts for what it needs

Give it a question pool released by the NCVEC, as the released PDF or a
text dump of one, and it builds an exam the way a VEC does: one question
drawn at random from each subelement group in the pool. Technician has 35
groups, so a Technician exam is 35 questions. General and Extra work the
same way with nothing to change here.

Answers are written to a file as you give them, so an interrupted session
keeps what you already answered and that file can be rescored later.

Reading a PDF needs pdftotext, from poppler-utils. A text dump avoids it.
"""
import os
import re
import sys
import random
import shutil
import argparse
import datetime
import tempfile
import subprocess
import collections

QUESTION = re.compile(
    r'^([TGE][0-9][A-Z][0-9]{2})\s+\(([A-D])\)(?:\s*\[([^\]]+)\])?\n(.*?)\n~~',
    re.S | re.M,
)

# Where poppler installs pdftotext when it is not already on PATH.
PDFTOTEXT_PATHS = (
    "/usr/bin/pdftotext",
    "/usr/local/bin/pdftotext",
    "/opt/homebrew/bin/pdftotext",
    "/opt/local/bin/pdftotext",
    r"C:\Program Files\poppler\bin\pdftotext.exe",
)

PASS_PERCENT = 74
VALID = ("A", "B", "C", "D")


def find_pdftotext():
    for path in PDFTOTEXT_PATHS:
        if os.path.isfile(path):
            return path
    found = shutil.which("pdftotext")
    if found:
        return found
    sys.exit(
        "Cannot read a PDF pool: pdftotext is not installed.\n"
        "Install poppler-utils (Debian/Ubuntu: sudo apt install poppler-utils; "
        "macOS: brew install poppler), or pass a text dump of the pool with "
        "--pool pool.txt instead."
    )


def dump_path(pool_path):
    """Where a PDF pool's text dump is cached, or None for a text pool."""
    if not pool_path.lower().endswith(".pdf"):
        return None
    return pool_path[: -len(".pdf")] + ".txt"


def pool_text(path):
    """Return the pool text, converting a PDF with pdftotext if needed.

    pdftotext's default (non-layout) output is what QUESTION is written
    against; adding -layout will break block matching.
    """
    if not path.lower().endswith(".pdf"):
        with open(path) as f:
            return f.read()

    pdftotext = find_pdftotext()
    beside = dump_path(path)

    if os.access(os.path.dirname(os.path.abspath(beside)), os.W_OK):
        if (not os.path.exists(beside)
                or os.path.getmtime(beside) < os.path.getmtime(path)):
            subprocess.run([pdftotext, path, beside], check=True)
        with open(beside) as f:
            return f.read()

    handle, scratch = tempfile.mkstemp(suffix=".txt")
    os.close(handle)
    try:
        subprocess.run([pdftotext, path, scratch], check=True)
        with open(scratch) as f:
            return f.read()
    finally:
        os.unlink(scratch)


def load_pool(path):
    text = pool_text(path).replace("\f", "")  # strip page-break artifacts

    pool = {}
    for qid, answer, reference, body in QUESTION.findall(text):
        pool[qid] = (answer, reference, re.sub(r'\n{2,}', '\n', body.strip()))
    if not pool:
        sys.exit(f"No questions found in {path}. Is it an NCVEC question pool?")
    return pool


def groups_of(pool):
    return sorted({qid[:3] for qid in pool})


def pass_mark(total):
    """Questions needed to pass: 74%, rounded up.

    Gives 26 of 35 and 37 of 50, the published FCC thresholds.
    """
    return -(-PASS_PERCENT * total // 100)


def build_exam(pool, rng):
    by_group = collections.defaultdict(list)
    for qid in pool:
        by_group[qid[:3]].append(qid)

    exam = [rng.choice(by_group[group]) for group in groups_of(pool)]
    rng.shuffle(exam)
    return exam


def ask(qid, position, total, reference, body):
    print(f"\nQuestion {position}/{total}  [{qid}]"
          + (f"  (Ref: {reference})" if reference else ""))
    print(body)
    while True:
        answer = input("Your answer (A/B/C/D, or 'q' to abandon): ")
        answer = answer.strip().upper()
        if answer in VALID or answer == "Q":
            return answer
        print(f"Enter one of {', '.join(VALID)}, or 'q'.")


def check_answers_path(answers_path, pool_path):
    """Refuse to write answers over the pool or its cached text dump."""
    protected = {os.path.realpath(pool_path)}
    dump = dump_path(pool_path)
    if dump:
        protected.add(os.path.realpath(dump))

    if os.path.realpath(answers_path) in protected:
        sys.exit(
            f"Refusing to write answers to {answers_path}: that is the pool "
            "file or the text dump made from it, and writing there would "
            "destroy it. Choose another path."
        )


def take_exam(pool, answers_path, rng):
    exam = build_exam(pool, rng)
    print(f"{len(exam)} questions, one from each group. "
          f"{pass_mark(len(exam))} correct to pass.")
    print(f"Answers are saved to {answers_path} when you finish.")

    given = []
    for position, qid in enumerate(exam, 1):
        _answer, reference, body = pool[qid]
        answer = ask(qid, position, len(exam), reference, body)
        if answer == "Q":
            print(f"\nAbandoned after {position - 1} of {len(exam)}. "
                  "Nothing saved.")
            return None
        given.append((qid, answer))

    with open(answers_path, "w") as out:
        for qid, answer in given:
            out.write(f"{qid} {answer}\n")
    return given


def read_answers(path):
    given = []
    with open(path) as f:
        for line in f:
            if line.strip():
                qid, answer = line.split()[:2]
                given.append((qid, answer.upper()))
    return given


def report(given, pool):
    unknown = [qid for qid, _ in given if qid not in pool]
    if unknown:
        sys.exit(f"Not in this pool: {', '.join(unknown)}. Wrong pool file?")

    missed = [(qid, ans) for qid, ans in given if pool[qid][0] != ans]
    total = len(given)
    correct = total - len(missed)
    needed = pass_mark(total)

    print(f"\nScore: {correct}/{total} = {100 * correct / total:.1f}%"
          f"   {'PASS' if correct >= needed else 'FAIL'} (need {needed}/{total})")

    print("\nBy subelement:")
    seen = collections.Counter(qid[:2] for qid, _ in given)
    wrong = collections.Counter(qid[:2] for qid, _ in missed)
    # Subelement 0 is last in the pool, not first, despite sorting that way.
    for subelement in sorted(seen, key=lambda s: (s[1] == "0", s)):
        asked = seen[subelement]
        print(f"  {subelement}: {asked - wrong[subelement]}/{asked}")

    if not missed:
        print("\nNothing missed.")
        return

    print(f"\nMissed {len(missed)}:")
    for qid, ans in missed:
        answer, _reference, body = pool[qid]
        print(f"\n[{qid}] you answered {ans}, correct is {answer}")
        print(body)


def prompt(label, default=None):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default


def default_answers_path():
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return os.path.join(os.getcwd(), f"answers_{stamp}.txt")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Practice an FCC amateur radio exam from a question pool.",
    )
    parser.add_argument("--pool", help="question pool, PDF or text dump")
    parser.add_argument("--answers", help="file to record answers in")
    parser.add_argument("--score", help="score this answers file, no exam")
    args = parser.parse_args()

    if args.pool is None:
        args.pool = prompt("Question pool file")
    if args.answers is None and args.score is None:
        args.answers = prompt("Answers file", default_answers_path())
    return args


def main():
    args = parse_args()

    if args.score:
        report(read_answers(args.score), load_pool(args.pool))
        return

    check_answers_path(args.answers, args.pool)
    pool = load_pool(args.pool)
    given = take_exam(pool, args.answers, random.Random())
    if given is not None:
        report(given, pool)


if __name__ == "__main__":
    main()
