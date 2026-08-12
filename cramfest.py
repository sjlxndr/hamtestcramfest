#!/usr/bin/env python3
"""
Ham radio license exam practice, driven by an FCC question pool.

Usage:
    cramfest.py --pool <pool>                        take an exam
    cramfest.py --pool <pool> --score <answers>      score a saved file
    cramfest.py --pool <pool> --weak <answers>...    rank weak areas
    cramfest.py --pool <pool> --drill <area>         drill one area
    cramfest.py --pool <pool> --feedback             study with answers shown
    cramfest.py                                      prompts for the pool

Give it a question pool released by the NCVEC, as the released PDF or a
text dump of one, and it builds an exam the way a VEC does: one question
drawn at random from each subelement group in the pool. Technician has 35
groups, so a Technician exam is 35 questions. General and Extra work the
same way with nothing to change here.

A finished exam or drill is written to <element>_<kind>_<timestamp>.txt in
the working directory, and --score reads one back. Stopping early discards
it, because finishing is the point; --feedback is the exception, keeping
what was answered, since it works through the whole pool.

Scoring needs the pool the answers came from. The filename names the
element, but two releases of the same element are indistinguishable by it
and can hold a different correct answer under the same question ID, which
is what the header inside the file is for.

Reading a PDF needs pdftotext, from poppler-utils. A text dump avoids it.
Linking a question's figure additionally needs tesseract.
"""
import os
import re
import sys
import random
import shutil
import argparse
import datetime
import tempfile
import pathlib
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

Question = collections.namedtuple("Question", "answer reference body")

# Question ID prefixes, matching _ID's character class.
ELEMENTS = {"T": "technician", "G": "general", "E": "extra"}

# Opens an answers file, naming the pool the answers were given against.
POOL_HEADER = "# pool:"

SEARCH_URL = "https://www.google.com/search?q="

# How a question names the figure it needs. Technician writes T-1, General
# and Extra carry the subelement digit, as in G7-1 and E5-1.
FIGURE = re.compile(r'figure\s+([TGE][0-9]?-[0-9]+)', re.I)

# Caches the label OCR read for each extracted image, so a pool is only
# read once.
FIGURE_INDEX = "figures.index"

# Where the Windows installer puts tesseract. Unlike poppler's winget
# package it does not reliably land on PATH, and figure links are the only
# thing that needs it.
TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)

# Every file this touches is UTF-8, because that is what pdftotext writes.
# Naming the codec rather than taking the locale's keeps it that way on a
# machine whose locale says otherwise, where the pool's curly quotes and
# en-dashes would otherwise raise. Bad bytes become replacement characters:
# a mangled question still lets you take the exam, a traceback does not.
TEXT = {"encoding": "utf-8", "errors": "replace"}


def find_binary(name, known):
    """A tool from its usual home, or from PATH, or None."""
    for path in known:
        if os.path.isfile(path):
            return path
    return shutil.which(name)


def find_pdftotext():
    found = find_binary("pdftotext", PDFTOTEXT_PATHS)
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


def writable_beside(path):
    """Whether a file can be created at this path, cache falling back if not."""
    return os.access(os.path.dirname(os.path.abspath(path)), os.W_OK)


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

    if writable_beside(beside):
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
            questions.append((head.group(1), Question(head.group(2), head.group(3),
                                                  "\n".join(parts))))

    opens = next((n for n, q in enumerate(questions)
                  if q[0][1:] == POOL_OPENS), None)
    if opens is None:
        sys.exit(
            f"Cannot find where the pool starts in {path}: no question "
            f"numbered {POOL_OPENS}. Is it an NCVEC question pool?"
        )

    return dict(questions[opens:])


def pass_mark(total):
    """Questions needed to pass: 74%, rounded up.

    Gives 26 of 35 and 37 of 50, the published FCC thresholds.
    """
    return -(-PASS_PERCENT * total // 100)


def build_exam(pool, rng):
    by_group = collections.defaultdict(list)
    for qid in pool:
        by_group[qid[:3]].append(qid)

    exam = [rng.choice(qids) for qids in by_group.values()]
    rng.shuffle(exam)
    return exam


def find_tesseract():
    """Tesseract, or None. Figure links are optional; the rest works without."""
    return find_binary("tesseract", TESSERACT_PATHS)


def read_caption(tesseract, image):
    """The figure label printed in an image, or None.

    Retried once in sparse-text mode. Neither mode reads every figure: the
    default misses the small Smith chart of E9-3, sparse mode misses E6-3.
    Thirteen of the fourteen figures in the three pools read first time.
    """
    for mode in ([], ["--psm", "11"]):
        seen = subprocess.run([tesseract, image, "-", *mode],
                              capture_output=True, text=True, **TEXT)
        found = FIGURE.search(seen.stdout)
        if found:
            return found.group(1).upper()
    return None


def extract_figures(pool_path, cache, pdfimages, tesseract):
    """Pull the pool's figures out and label each by reading its caption.

    Position cannot stand in for the caption. Extra ships a soft mask for
    every figure, so its twenty extracted files hold ten figures, and its
    numbering jumps from E7-3 to E9-1, so nothing about the order is
    derivable.
    """
    listing = subprocess.run([pdfimages, "-list", pool_path],
                             capture_output=True, text=True, **TEXT)
    kinds = [row.split()[2] for row in listing.stdout.splitlines()[2:]]

    subprocess.run([pdfimages, "-png", pool_path, os.path.join(cache, "fig")],
                   check=True, capture_output=True)
    written = sorted(f for f in os.listdir(cache) if f.endswith(".png"))

    figures = {}
    for kind, name in zip(kinds, written):
        if kind != "image":
            continue
        label = read_caption(tesseract, os.path.join(cache, name))
        if label:
            figures[label] = name
    return figures


def load_figures(pool_path):
    """Figure label to image path, empty when figures cannot be had.

    A text pool holds no images, and without tesseract an extracted image
    cannot be told from any other, so both yield nothing and every
    affected question falls back to naming the figure.
    """
    if not pool_path.lower().endswith(".pdf"):
        return {}

    tesseract = find_tesseract()
    pdfimages = shutil.which("pdfimages") or os.path.join(
        os.path.dirname(find_pdftotext()), "pdfimages")
    if tesseract is None or not os.path.isfile(pdfimages):
        return {}

    cache = pool_path[: -len(".pdf")] + ".figures"
    if not writable_beside(cache):
        cache = tempfile.mkdtemp(suffix=".figures")
    os.makedirs(cache, exist_ok=True)

    index = os.path.join(cache, FIGURE_INDEX)
    if not os.path.exists(index):
        found = extract_figures(pool_path, cache, pdfimages, tesseract)
        with open(index, "w", **TEXT) as f:
            for label, name in sorted(found.items()):
                f.write(f"{label} {name}\n")

    figures = {}
    with open(index, **TEXT) as f:
        for line in f:
            if line.strip():
                label, name = line.split()
                figures[label] = os.path.join(cache, name)
    return figures


def with_figures(body, figures):
    """The question text, with its figure reference turned into a link.

    The reference is linked where it stands, so the words the question
    already uses are what the reader clicks. Where no image can be
    offered, the reference is left as written and a line naming the figure
    follows instead: the question always says which figure it wants, so
    the reader can be told what to look up regardless.
    """
    reference = FIGURE.search(body)
    if not reference:
        return body

    label = reference.group(1).upper()
    image = figures.get(label)
    if image is None:
        return f"{body}\nRefer to PDF for Figure {label}"

    linked = hyperlink(pathlib.Path(image).resolve().as_uri(), reference.group(0))
    return body[:reference.start()] + linked + body[reference.end():]


def ask(qid, position, total, reference, body, figures):
    print(f"\nQuestion {position}/{total}  [{qid}]"
          + (f"  (Ref: {reference})" if reference else ""))
    print(with_figures(body, figures))
    while True:
        answer = input("Your answer (A/B/C/D, or 'q' to stop): ")
        answer = answer.strip().upper()
        if answer in VALID or answer == "Q":
            return answer
        print(f"Enter one of {', '.join(VALID)}, or 'q'.")


def write_answers(out_path, pool_path, given):
    with open(out_path, "w", **TEXT) as out:
        out.write(f"{POOL_HEADER} {pool_name(pool_path)}\n")
        for qid, answer in given:
            out.write(f"{qid} {answer}\n")


def verdict(qid, question, answer):
    """Right or wrong, what the answer was, and where to read up on it.

    The link is offered either way, unlike a report, which only links what
    was missed. Here you are studying rather than being marked, and a
    lucky guess is worth reading about as much as a wrong one.
    """
    if answer == question.answer:
        said = "  Correct."
    else:
        named = f"The answer is {question.answer}."
        for line in question.body.split("\n"):
            if line.startswith(f"{question.answer}."):
                named = line
                break
        said = f"  Incorrect. {named}"

    # Blank line first: the verdict lands right under what was typed
    # otherwise, and reads as part of the prompt.
    return f"\n{said}\n  {explain_link(qid, question.body)}"


def administer(pool, pool_path, questions, out_path, figures, feedback=False):
    """Ask each question in turn, saving what was answered.

    With feedback, the answer follows each question. An out_path of None
    writes nothing at all, which is what feedback wants: the verdicts are
    the output, so there is no file to keep or discard.
    """
    given = []
    for position, qid in enumerate(questions, 1):
        question = pool[qid]
        answer = ask(qid, position, len(questions), question.reference,
                     question.body, figures)
        if answer == "Q":
            print(f"\nStopped after {position - 1} of {len(questions)}.")
            if out_path:
                print("Nothing saved.")
            return None
        given.append((qid, answer))
        if feedback:
            print(verdict(qid, question, answer))

    if out_path:
        write_answers(out_path, pool_path, given)
    return given


def take_exam(pool, pool_path, out_path, rng, figures):
    exam = build_exam(pool, rng)
    print(f"{len(exam)} questions, one from each group. "
          f"{pass_mark(len(exam))} correct to pass.")
    print(f"Answers are saved to {out_path} when you finish.")
    return administer(pool, pool_path, exam, out_path, figures)


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


def hyperlink(url, label):
    """An OSC 8 terminal hyperlink.

    Terminals that do not understand OSC 8 print the label alone, so the
    line stays readable either way.
    """
    return f"\033]8;;{url}\033\\{label}\033]8;;\033\\"


def explain_link(qid, body):
    """An OSC 8 hyperlink to a search for the question.

    The question ID leads the query: study sites index the pool by it, so
    it finds material about this exact question rather than the topic in
    general.
    """
    query = urllib.parse.quote_plus(
        f"Explain this ham radio question: {qid} {asked(body)}")
    return hyperlink(SEARCH_URL + query, "Explain this question")


def missed_in(given, pool):
    """The questions answered wrongly, refusing answers the pool lacks."""
    unknown = [qid for qid, _ in given if qid not in pool]
    if unknown:
        sys.exit(f"Not in this pool: {', '.join(unknown)}. Wrong pool file?")
    return [(qid, ans) for qid, ans in given if pool[qid].answer != ans]


def show_missed(missed, pool, figures):
    if not missed:
        print("\nNothing missed.")
        return

    print(f"\nMissed {len(missed)}:")
    for qid, ans in missed:
        question = pool[qid]
        print(f"\n[{qid}] you answered {ans}, correct is {question.answer}")
        print(with_figures(question.body, figures))
        print(explain_link(qid, question.body))


def report(given, pool, figures):
    missed = missed_in(given, pool)
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

    show_missed(missed, pool, figures)


def report_drill(given, pool, figures):
    """No pass mark: 74% is an exam threshold and says nothing here."""
    missed = missed_in(given, pool)
    total = len(given)
    correct = total - len(missed)
    print(f"\nScore: {correct}/{total} = {100 * correct / total:.1f}%")
    show_missed(missed, pool, figures)


def prompt(label, default=None):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default


def session_path(pool, kind):
    """Name a finished session after its element and the time it was taken.

    The element tells you which pool to hand back to --score; it does not
    distinguish two releases of the same element, which is what the header
    inside the file is for. Drills carry their area too, so a glob for the
    exam files does not collect them.
    """
    element = ELEMENTS[next(iter(pool))[0]]
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return os.path.join(os.getcwd(), f"{element}_{kind}_{stamp}.txt")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Practice an FCC amateur radio exam from a question pool.",
    )
    parser.add_argument("--pool", help="question pool, PDF or text dump")
    parser.add_argument("--score", help="score this answers file, no exam")
    parser.add_argument("--weak", nargs="+", metavar="FILE",
                        help="report weak areas across these answers files")
    parser.add_argument("--drill", metavar="AREA",
                        help="drill a subelement like T8 or a group like T8C")
    parser.add_argument("--count", type=int, metavar="N",
                        help="ask at most N of them, if the area holds more")
    parser.add_argument("--feedback", action="store_true",
                        help="work through the pool, told the answer each time")
    args = parser.parse_args()

    if args.pool is None:
        args.pool = prompt("Question pool file")
    return args


def weak_areas(paths, pool):
    """Wrong and asked counts per subelement and per group, over every file."""
    wrong = collections.Counter()
    asked = collections.Counter()
    unknown = []
    for path in paths:
        _recorded, given = read_answers(path)
        for qid, answer in given:
            if qid not in pool:
                unknown.append(qid)
                continue
            for key in (qid[:2], qid[:3]):
                asked[key] += 1
                if pool[qid].answer != answer:
                    wrong[key] += 1
    return wrong, asked, unknown


def weakest(keys, wrong, asked):
    """Worst first, then by how much was asked, then by name."""
    return sorted(keys, key=lambda k: (-wrong[k] / asked[k], -asked[k], k))


def under(groups, ranked_subelements):
    """Groups beneath their subelement, in the subelement ranking's order.

    Lines the group table up with the subelement table above it, so the
    groups that drove a subelement's rank sit together under it.
    """
    rank = {name: place for place, name in enumerate(ranked_subelements)}
    return sorted(groups, key=lambda g: (rank[g[:2]], g))


def report_weak(paths, pool):
    wrong, asked, unknown = weak_areas(paths, pool)
    if not asked:
        sys.exit("No questions in those files are in this pool.")

    answers = sum(asked[k] for k in asked if len(k) == 2)
    print(f"{answers} answers over {len(paths)} file(s)\n")

    subelements = [k for k in asked if len(k) == 2]
    groups = [k for k in asked if len(k) == 3 and wrong[k]]

    ranked = weakest(subelements, wrong, asked)
    for title, ordered in (
            ("By subelement, weakest first", ranked),
            ("By group, under the subelement ranking", under(groups, ranked)),
            ("By group, weakest first", weakest(groups, wrong, asked)),
    ):
        print(title)
        for key in ordered:
            share = 100 * wrong[key] / asked[key]
            print(f"  {key:<4} {share:5.1f}%   {wrong[key]} of {asked[key]} wrong")
        if not ordered:
            print("  nothing missed")
        print()

    if unknown:
        seen = sorted(set(unknown))
        print(f"Not in this pool, and not counted: {', '.join(seen)}")


def drill_questions(pool, area, count, rng):
    """The questions in a subelement or group, shuffled, optionally fewer.

    A count outside what the area holds asks all of it: nothing sensible
    is meant by fewer than one, and asking for more than exists is just
    asking for everything.
    """
    area = area.upper() if area else ""
    chosen = [qid for qid in pool if qid.startswith(area)]
    if not chosen:
        sys.exit(f"No questions in {area}. Give a subelement like T8, "
                 "or a group like T8C.")

    rng.shuffle(chosen)
    if count is not None and 1 <= count < len(chosen):
        chosen = chosen[:count]
    return chosen


def study(pool, pool_path, area, count, rng, figures):
    """Work through the pool, or one area of it, told the answer each time.

    Nothing is scored and nothing is written: the verdict after each
    question is the whole output.
    """
    questions = drill_questions(pool, area, count, rng)
    where = f" from {area.upper()}" if area else ""
    print(f"{len(questions)} questions{where}, with the answer after each.")
    administer(pool, pool_path, questions, None, figures, feedback=True)


def take_drill(pool, pool_path, area, count, rng, figures):
    questions = drill_questions(pool, area, count, rng)
    out_path = session_path(pool, f"drill_{area.upper()}")
    print(f"{len(questions)} questions from {area.upper()}.")
    print(f"Answers are saved to {out_path} when you finish.")
    return administer(pool, pool_path, questions, out_path, figures)


def main():
    # A terminal whose encoding cannot represent the pool's curly quotes
    # would otherwise raise mid-question. Printing them as "?" is worse to
    # read and better than stopping the exam.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")

    args = parse_args()

    if args.feedback:
        pool = load_pool(args.pool)
        study(pool, args.pool, args.drill, args.count, random.Random(),
              load_figures(args.pool))
        return

    if args.drill:
        pool = load_pool(args.pool)
        figures = load_figures(args.pool)
        given = take_drill(pool, args.pool, args.drill, args.count,
                           random.Random(), figures)
        if given is not None:
            report_drill(given, pool, figures)
        return

    if args.weak:
        report_weak(args.weak, load_pool(args.pool))
        return

    if args.score:
        recorded, given = read_answers(args.score)
        print(f"Answers recorded against: {recorded or 'unrecorded'}")
        print(f"Scoring against:          {pool_name(args.pool)}")
        report(given, load_pool(args.pool), load_figures(args.pool))
        return

    pool = load_pool(args.pool)
    figures = load_figures(args.pool)
    given = take_exam(pool, args.pool, session_path(pool, "answers"),
                      random.Random(), figures)
    if given is not None:
        report(given, pool, figures)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        sys.exit(130)  # conventional for SIGINT
    except EOFError:
        print("\nInput ended.", file=sys.stderr)
        sys.exit(1)
    except OSError as problem:
        # A missing or unreadable pool, or nowhere to write the answers.
        where = f": {problem.filename}" if problem.filename else ""
        print(f"{problem.strerror}{where}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as problem:
        print(f"{os.path.basename(problem.cmd[0])} failed "
              f"({problem.returncode}) on {problem.cmd[-1]}", file=sys.stderr)
        sys.exit(1)
    except Exception as problem:  # noqa: BLE001 - a CLI owes no traceback
        print(f"{type(problem).__name__}: {problem}", file=sys.stderr)
        sys.exit(1)
