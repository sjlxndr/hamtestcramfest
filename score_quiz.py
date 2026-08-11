#!/usr/bin/env python3
"""
Score a completed quiz against the answer key.

Usage:
    python3 score_quiz.py answers.txt
    cat answers.txt | python3 score_quiz.py

Input: one "QUESTION_ID YOUR_ANSWER" pair per line, e.g.:
    T0C07 B
    T4A09 B
    T4A12 C
    ...

Looks up correct answers in answerkey.txt and question text/choices in
the Technician Pool text file (via extract_questions.load_pool), then
prints a score summary and the full text of any missed questions.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_questions import load_pool

ANSWERKEY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "answerkey.txt"
)


def load_answerkey(path=ANSWERKEY_FILE):
    key = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            qid, letter = parts[0], parts[1]
            key[qid] = letter
    return key


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    answers = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        answers.append((parts[0], parts[1].upper()))

    key = load_answerkey()
    pool = load_pool()

    correct = 0
    missed = []
    total = len(answers)

    for i, (qid, your_ans) in enumerate(answers, 1):
        correct_ans = key.get(qid)
        if correct_ans is None:
            print(f"WARNING: {qid} not found in answer key", file=sys.stderr)
            continue
        ok = your_ans == correct_ans
        status = "OK" if ok else "MISS"
        print(f"{i:2d} {qid} you={your_ans} correct={correct_ans} {status}")
        if ok:
            correct += 1
        else:
            missed.append((i, qid, your_ans, correct_ans))

    pct = correct / total * 100 if total else 0
    passing = total * 0.74
    result = "PASS" if correct >= passing else "FAIL"
    print(f"\nSCORE: {correct}/{total} = {pct:.1f}% ({result}, passing is {passing:.0f}/{total} = 74%)")

    if missed:
        print("\nMISSED QUESTIONS:")
        for i, qid, your_ans, correct_ans in missed:
            body = pool.get(qid, (None, None, "(question text not found)"))[2]
            print(f"\n#{i} {qid} — you answered {your_ans}, correct is {correct_ans}")
            print(body)


if __name__ == "__main__":
    main()
