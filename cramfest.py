#!/usr/bin/env python3
"""
Ham radio license exam practice, driven by an FCC question pool.

Usage:
    python3 cramfest.py --pool pool.pdf
    python3 cramfest.py --pool pool.pdf --score technician_answers_....txt
    python3 cramfest.py                     # prompts for the pool

A finished exam is written to <element>_answers_<timestamp>.txt in the
working directory, and --score reads one back. Scoring needs the pool the
exam came from; the filename names the element so you know which one, but
two releases of the same element are indistinguishable and can hold a
different correct answer under the same question ID.

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
import urllib.parse

_ID = r'[TGE][0-9][A-Z][0-9]{2}'

# What a question opens with: its ID, the correct answer, an optional rule
# reference. Deliberately unanchored. A PDF holds positioned glyphs rather
# than lines, so pdftotext and a viewer's copy-paste each guess where the
# lines break and guess differently; matching on position instead of line
# structure is what makes the parser indifferent to which one produced the
# text.
HEADER = re.compile(rf'({_ID})\s+\(([A-D])\)\s*(?:\[([^\]]+)\])?')

# The pool body opens with question 01 of group 1A. Everything before it is
# errata, syllabus and cover pages.
POOL_OPENS = "1A01"

# Closes a question's content. Not a delimiter, but without trimming here the
# last choice swallows it along with any page furniture between questions.
TERMINATOR = "~~"

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

# Question ID prefixes, matching _ID's character class.
ELEMENTS = {"T": "technician", "G": "general", "E": "extra"}

# Opens an answers file, naming the pool the answers were given against.
POOL_HEADER = "# pool:"

SEARCH_URL = "https://www.google.com/search?q="

# Every file this touches is UTF-8, because that is what pdftotext writes.
# Naming the codec rather than taking the locale's keeps it that way on a
# machine whose locale says otherwise, where the pool's curly quotes and
# en-dashes would otherwise raise. Bad bytes become replacement characters:
# a mangled question still lets you sit the exam, a traceback does not.
TEXT = {"encoding": "utf-8", "errors": "replace"}


def find_pdftotext():
    for path in PDFTOTEXT_PATHS:
        if os.path.isfile(path):
            return path
    found = shutil.which("pdftotext")
    if found:
        return found
    sys.exit(
        "Cannot read a PDF pool: pdftotext is not installed.\n"
        "  Debian/Ubuntu: sudo apt install poppler-utils\n"
        "  macOS:         brew install poppler\n"
        "  Windows:       winget install -e --id Schard.Poppler\n"
        "Or skip it: paste the pool out of a PDF viewer into a text file and "
        "pass that with --pool instead."
    )


def pool_name(pool_path):
    """The pool's own filename, which carries its release date range.

    Symlinks are resolved: the link's name identifies nothing, while the
    target's distinguishes one release of an element from the next.
    """
    return os.path.basename(os.path.realpath(pool_path))


def dump_path(pool_path):
    """Where a PDF pool's text dump is cached, or None for a text pool."""
    if not pool_path.lower().endswith(".pdf"):
        return None
    return pool_path[: -len(".pdf")] + ".txt"


def pool_text(path):
    """Return the pool text, converting a PDF with pdftotext if needed.

    Default flags. -layout also parses, since nothing here depends on
    where lines fall, but it disagrees with the default on one question's
    wording, so there is no reason to prefer it.
    """
    if not path.lower().endswith(".pdf"):
        with open(path, **TEXT) as f:
            return f.read()

    pdftotext = find_pdftotext()
    beside = dump_path(path)

    if os.access(os.path.dirname(os.path.abspath(beside)), os.W_OK):
        if (not os.path.exists(beside)
                or os.path.getmtime(beside) < os.path.getmtime(path)):
            subprocess.run([pdftotext, path, beside], check=True)
        with open(beside, **TEXT) as f:
            return f.read()

    handle, scratch = tempfile.mkstemp(suffix=".txt")
    os.close(handle)
    try:
        subprocess.run([pdftotext, path, scratch], check=True)
        with open(scratch, **TEXT) as f:
            return f.read()
    finally:
        os.unlink(scratch)


def split_choices(content):
    """The question and its four choices, or None if all four are not there.

    Each marker is the first occurrence after the previous one, and no
    whitespace is required around it in either direction. The published
    Extra pool contains "UHF D.A DX spotting system" with no space after
    the period, and copied text welds the other way, as in "the aircraftB.
    The amateur station".
    """
    cuts, at = [], 0
    for letter in "ABCD":
        found = content.find(f"{letter}.", at)
        if found == -1:
            return None
        cuts.append(found)
        at = found + 2

    parts = [content[:cuts[0]]]
    parts += [content[a:b] for a, b in zip(cuts, cuts[1:] + [len(content)])]
    return [part.strip() for part in parts]


def load_pool(path):
    text = " ".join(pool_text(path).split())  # position, not line structure
    headers = list(HEADER.finditer(text))

    questions = []
    for n, head in enumerate(headers):
        end = headers[n + 1].start() if n + 1 < len(headers) else len(text)
        content = text[head.end():end]
        stop = content.find(TERMINATOR)
        if stop != -1:
            content = content[:stop]

        parts = split_choices(content)
        if parts:  # a header with nothing question-shaped after it is not one
            questions.append((head.group(1), head.group(2), head.group(3), parts))

    opens = next((n for n, q in enumerate(questions)
                  if q[0][1:] == POOL_OPENS), None)
    if opens is None:
        sys.exit(
            f"Cannot find where the pool starts in {path}: no question "
            f"numbered {POOL_OPENS}. Is it an NCVEC question pool?"
        )

    return {qid: (answer, reference, "\n".join(parts))
            for qid, answer, reference, parts in questions[opens:]}


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


def take_exam(pool, pool_path, out_path, rng):
    exam = build_exam(pool, rng)
    print(f"{len(exam)} questions, one from each group. "
          f"{pass_mark(len(exam))} correct to pass.")
    print(f"Answers are saved to {out_path} when you finish.")

    given = []
    for position, qid in enumerate(exam, 1):
        _answer, reference, body = pool[qid]
        answer = ask(qid, position, len(exam), reference, body)
        if answer == "Q":
            print(f"\nAbandoned after {position - 1} of {len(exam)}. "
                  "Nothing saved.")
            return None
        given.append((qid, answer))

    with open(out_path, "w", **TEXT) as out:
        out.write(f"{POOL_HEADER} {pool_name(pool_path)}\n")
        for qid, answer in given:
            out.write(f"{qid} {answer}\n")
    return given


def read_answers(path):
    """Return the pool named in the header, or None, and the answers."""
    recorded = None
    given = []
    with open(path, **TEXT) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if line.startswith(POOL_HEADER):
                    recorded = line[len(POOL_HEADER):].strip()
                continue
            qid, answer = line.split()[:2]
            given.append((qid, answer.upper()))
    return recorded, given


def asked(body):
    """The question itself, without its answer choices.

    Choices are dropped so the search query is the question and nothing
    else; every question in every pool opens its choices with an "A." line.
    """
    question = body.split("\n")
    cut = next(i for i, line in enumerate(question) if re.match(r'A\.\s', line))
    return " ".join(question[:cut]).strip()


def explain_link(body):
    """An OSC 8 hyperlink to a search for the question.

    Terminals that do not understand OSC 8 print the label alone, so the
    line stays readable either way.
    """
    query = urllib.parse.quote_plus(f"Explain this ham radio question: {asked(body)}")
    return f"\033]8;;{SEARCH_URL}{query}\033\\Explain this question\033]8;;\033\\"


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
        print(explain_link(body))


def prompt(label, default=None):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default


def answers_path(pool):
    """Name the answers file after the exam it came from.

    The element is the only pool identity carried anywhere, so it goes in
    the filename: it tells you which pool to hand back to --score. It does
    not distinguish two releases of the same element.
    """
    element = ELEMENTS[next(iter(pool))[0]]
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return os.path.join(os.getcwd(), f"{element}_answers_{stamp}.txt")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Practice an FCC amateur radio exam from a question pool.",
    )
    parser.add_argument("--pool", help="question pool, PDF or text dump")
    parser.add_argument("--score", help="score this answers file, no exam")
    args = parser.parse_args()

    if args.pool is None:
        args.pool = prompt("Question pool file")
    return args


def main():
    # A terminal whose encoding cannot represent the pool's curly quotes
    # would otherwise raise mid-question. Printing them as "?" is worse to
    # read and better than stopping the exam.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")

    args = parse_args()

    if args.score:
        recorded, given = read_answers(args.score)
        print(f"Answers recorded against: {recorded or 'unrecorded'}")
        print(f"Scoring against:          {pool_name(args.pool)}")
        report(given, load_pool(args.pool))
        return

    pool = load_pool(args.pool)
    given = take_exam(pool, args.pool, answers_path(pool), random.Random())
    if given is not None:
        report(given, pool)


if __name__ == "__main__":
    main()
