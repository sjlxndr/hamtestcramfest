#!/usr/bin/env python3
"""
Generate a random question set and interactively quiz on it, recording
the answers. Combines what randoms.sh + a quiz loop would do.

Usage:
    python3 run_quiz.py                  # 35 random questions (default)
    python3 run_quiz.py 20                # 20 random questions
    python3 run_quiz.py 20 my_answers.txt

Question selection: picks N questions uniformly at random (with
replacement, same as randoms.sh's `SRANDOM % 409` approach -- so
occasional repeats within a set are possible, matching prior behavior)
from every ID listed in answerkey.txt.

Output: writes "QUESTION_ID YOUR_ANSWER" pairs to the given file (or an
auto-named answers_<timestamp>.txt) as you go, so progress survives an
interrupted session. That file is directly consumable by score_quiz.py.

Does not reveal correct/incorrect during the quiz -- scoring is a
separate step (score_quiz.py).
"""
import sys
import os
import random
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract_questions import load_pool

ANSWERKEY_FILE = os.path.join(HERE, "answerkey.txt")
VALID = {"A", "B", "C", "D"}


def load_all_ids(path=ANSWERKEY_FILE):
    with open(path) as f:
        return [line.split()[0] for line in f if line.strip()]


def prompt_answer(qid, i, total, ref, body):
    print(f"\nQuestion {i}/{total}  [{qid}]" + (f"  (Ref: {ref})" if ref else ""))
    print(body)
    while True:
        ans = input("Your answer (A/B/C/D, or 'q' to quit and save): ").strip().upper()
        if ans == "Q":
            return None
        if ans in VALID:
            return ans
        print("Please enter A, B, C, D, or q.")


def main():
    count = 35
    out_path = None
    args = sys.argv[1:]
    if args and args[0].isdigit():
        count = int(args[0])
        args = args[1:]
    if args:
        out_path = args[0]
    if out_path is None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out_path = os.path.join(HERE, f"answers_{ts}.txt")

    all_ids = load_all_ids()
    ids = [random.choice(all_ids) for _ in range(count)]

    pool = load_pool()
    total = len(ids)

    with open(out_path, "w") as out:
        for i, qid in enumerate(ids, 1):
            if qid not in pool:
                print(f"WARNING: {qid} not found in pool, skipping", file=sys.stderr)
                continue
            _, ref, body = pool[qid]
            ans = prompt_answer(qid, i, total, ref, body)
            if ans is None:
                print(f"\nStopped early at question {i}/{total}.")
                break
            out.write(f"{qid} {ans}\n")
            out.flush()

    print(f"\nAnswers saved to {out_path}")
    print(f"Score with: python3 score_quiz.py {out_path}")


if __name__ == "__main__":
    main()
