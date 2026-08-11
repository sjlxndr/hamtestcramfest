#!/usr/bin/env python3
"""
Extract question text/choices for a list of question IDs from the
Technician Pool.

Usage:
    python3 extract_questions.py --ids ids.txt --out quiz_questions.json
    python3 extract_questions.py          # prompts for the missing arguments

The pool may be given as either the released PDF or a text dump of one. A
PDF is converted with pdftotext to a sibling .txt beside it; that dump is
reused on later runs unless the PDF is newer.

The IDs file holds one question ID per line. The first whitespace-separated
token of each line is used, so raw `randoms.sh` output like "T1A01 C" works
directly. Output is a JSON object keyed by question ID:
[correct_answer_letter, rule_reference_or_null, question_and_choices_text]
"""
import re
import os
import sys
import json
import argparse
import subprocess

POOL_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "2026-2030 Technician Pool and Syllabus Public Release Feb 19 2026.pdf",
)

PATTERN = re.compile(
    r'^(T[0-9][A-Z][0-9]{2})\s+\(([A-D])\)(?:\s*\[([^\]]+)\])?\n(.*?)\n~~',
    re.S | re.M,
)


def pool_text(path):
    """Read the pool, dumping a PDF to a sibling .txt first if needed.

    pdftotext's default (non-layout) output is what PATTERN is written
    against; changing the flags will break block matching.
    """
    if path.lower().endswith(".pdf"):
        dump_path = path[: -len(".pdf")] + ".txt"
        if (not os.path.exists(dump_path)
                or os.path.getmtime(dump_path) < os.path.getmtime(path)):
            subprocess.run(["pdftotext", path, dump_path], check=True)
        path = dump_path

    with open(path) as f:
        return f.read()


def load_pool(path=POOL_FILE):
    text = pool_text(path)
    text = text.replace("\f", "")  # strip page-break artifacts

    blocks = {}
    for m in PATTERN.finditer(text):
        qid, ans, ref, body = m.groups()
        body = re.sub(r'\n{2,}', '\n', body.strip())
        blocks[qid] = (ans, ref, body)
    return blocks


def read_ids(path):
    with open(path) as f:
        return [line.split()[0] for line in f if line.strip()]


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
        description="Extract Technician Pool questions by ID into a JSON file.",
    )
    parser.add_argument("--pool", default=POOL_FILE, help="pool PDF or text dump")
    parser.add_argument("--ids", help="file of question IDs, one per line")
    parser.add_argument("--out", help="file to write the JSON output to")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        args.pool = prompt("Question pool file", POOL_FILE)
    if args.ids is None:
        args.ids = prompt("Question ID file")
    if args.out is None:
        args.out = prompt("Output JSON file")
    return args


def main():
    args = parse_args()

    ids = read_ids(args.ids)
    blocks = load_pool(args.pool)

    missing = [i for i in ids if i not in blocks]
    if missing:
        print(f"WARNING: {len(missing)} ID(s) not found: {missing}", file=sys.stderr)

    out = {i: blocks[i] for i in ids if i in blocks}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(out)} question(s) to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
