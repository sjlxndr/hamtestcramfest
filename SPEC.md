# Single-script exam tool

## Audience and purpose

Stephen reads this to approve the behavior before any test or line of code is
written. The implementer derives tests from **In scope** and nothing else.

## Background

Four scripts share the work today: `extract_questions.py` parses the pool,
`make_answerkey.py` derives `answerkey.txt`, `run_quiz.py` administers a quiz,
`score_quiz.py` scores the recorded answers. `answerkey.txt` is a materialized
cache of two projections of the pool, both available from a parse, so it earns
nothing. The goal is one shipped script that anyone holding a pool file can run.

## Conflicts between the stated constraints

Resolved here so no revision round argues about them again.

1. **"Ship one script" vs. four existing scripts.** The four are deleted, not
   deprecated and not left importable. Nothing in the new script refers to them.
2. **"Anyone with the pool file can run it" vs. depending on `pdftotext`.** A
   recipient without poppler cannot process a PDF at all. Resolved by accepting
   a `.txt` dump as an equal-status input and, on a PDF with no `pdftotext`,
   failing with a message naming `poppler-utils` and the `.txt` escape hatch.
3. **"Files as arguments, never stdio" vs. an interactive exam.** stdin carries
   *keystrokes* (answering a question), never *data* (the pool, the answer
   record). Pool and answer paths are arguments or prompts; they are never
   piped.
4. **"Runs anywhere" vs. caching the PDF dump beside the pool.** The pool may
   sit on read-only or shared storage. Resolved: the dump is written beside the
   pool when that directory is writable, and to a temporary file otherwise. The
   run never fails because the cache could not be written.
5. **"Self-contained script" vs. 12 questions that require a diagram.** Group
   T6C is 10/12 diagram-dependent and every exam draws from T6C, so 86% of
   exams contain a question the script cannot render. Resolved in documentation
   rather than in code: the README tells the reader to keep the pool PDF open
   for figures T-1, T-2 and T-3. The script has no notion of figures, does not
   detect the references, and treats those questions like any other.

## In scope

**Single script.** One file, `cramfest.py`, standard library only.
`extract_questions.py`, `make_answerkey.py`, `run_quiz.py`, `score_quiz.py` and
`answerkey.txt` are removed in the same change.

**Pool input.** Accepts the released pool as PDF or as a text dump. A PDF is
converted with `pdftotext` using default (non-layout) flags. The binary is
resolved by conventional install path with a `PATH` fallback; when absent, the
script exits naming `poppler-utils` as the prerequisite.

**Element-agnostic.** Nothing is hardcoded to Technician. Question IDs match
`[TGE][0-9][A-Z][0-9]{2}`, covering Technician, General and Extra. Exam shape is
derived from the pool, never configured.

**Exam construction.** The distinct 3-character group prefixes present in the
pool are collected; the exam draws exactly one question at random from each
group. Exam length is therefore the pool's group count: 35 for Technician,
whatever General and Extra carry. Questions are presented in random order.
Answer choices keep their pool letters and are not reordered.

**Answer recording.** Each answer is written to the answers file as it is given,
one `<question ID> <letter>` line per question, in the existing
`answers_<timestamp>.txt` format. The file is written in a single pass once the
exam is complete; answers are held in memory during the exam and scored from
there, never re-read from disk. Answering `q` abandons the attempt: nothing is
written and nothing is scored. The script refuses to record answers to the pool
file or to the text dump cached from it, both of which it would otherwise
truncate.

**Scoring.** Scoring runs at the end of an exam, and can also run against a
saved answers file without re-taking the exam. The report gives the score,
pass/fail against `ceil(0.74 x exam length)`, a per-subelement breakdown, and
each missed question with the correct answer.

**Documentation.** A `README.md` states what the script does, that the pool file
must be supplied by the reader, that `pdftotext` is required for PDF input, and
that 12 Technician questions depend on figures T-1, T-2 and T-3, which the
reader should have the pool PDF open to consult.

**Command line.** `--pool`, `--answers`, `--score` as file arguments; a bare run
prompts for them, offering defaults. No data on stdin or stdout.

### Acceptance criteria

1. Given the Technician pool, an exam contains exactly 35 questions, one from
   each of the 35 groups, with no repeats.
2. Repeated runs draw different questions; every question in a group is
   reachable across runs.
3. Given a pool with a different group count, exam length equals that count
   with no code change.
4. A `.txt` dump and its source PDF produce identical parses.
5. Scoring a known answers file reproduces the score by hand-check, and the
   pass threshold is 26 for a 35-question exam.
6. Abandoning an exam with `q` writes no answers file and reports no score.
7. With `pdftotext` unavailable and a PDF pool, the script exits naming
   `poppler-utils`; with a `.txt` pool it runs normally.
8. `README.md` names the figure limitation and the `pdftotext` prerequisite.
9. Pointing `--answers` at the pool file, or at the `.txt` dump of a PDF pool,
   exits without writing, and the pool is left byte-for-byte intact.

## Out of scope

- Anything to do with diagrams in the script: rendering them, extracting them,
  detecting the references, or flagging affected questions. Documentation
  covers it.
- Any GUI, web interface, or TUI beyond line-by-line prompts.
- Resuming an interrupted exam. Quitting discards the attempt, and the answers
  file is deliberately not a checkpoint.
- Progress tracking across sessions, spaced repetition, or weighting toward
  previously missed questions.
- Shuffling or renaming answer choices.
- Validating or correcting the pool beyond parsing it.
- Reproducing the existing per-subelement study quizzes.

## Deferred

- Opening the pool PDF to the page holding a referenced figure.
- A study mode that drills a single subelement rather than a full exam.
- A seed argument for reproducible exams.

## Assumptions

- The script is named `cramfest.py`, after the repository.
- Exam length equals the pool's group count. Verified against all three pools:
  Technician 409 questions / 35 groups, General 423 / 35, Extra 598 / 50,
  giving the published exam lengths of 35, 35 and 50.
- The pass threshold is `ceil(0.74 x exam length)`, giving 26 of 35 and 37 of
  50, matching the published FCC thresholds.
- Questions are presented in random rather than group order.
- `.gitignore` needs explicit `!/SPEC.md` and `!/README.md` negations, because
  its deny-all whitelist would otherwise refuse both files. `!/*.md` is not
  used, as it would re-admit the personal study records the whitelist exists to
  exclude.
