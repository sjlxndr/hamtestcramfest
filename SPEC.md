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

**Answer recording.** Answers are held in memory for the duration of the exam
and scored from there, never re-read from disk. A completed exam is written in a
single pass to `<element>_answers_<timestamp>.txt` in the working directory: a
`# pool: <filename>` header naming the pool the answers were given against, then
one `<question ID> <letter>` line per question. Answering `q` abandons the
attempt: nothing is written and nothing is scored.

The path is not configurable. An auto-named file cannot collide with the pool or
its text dump, so there is no overwrite to guard against. The element in the
filename says which pool to reach for; the header says which release, recording
the pool's own filename with symlinks resolved, because that filename carries
the release date range and a question ID does not.

`--score` prints the recorded pool alongside the one it is scoring against, so a
mismatch is visible. It does not refuse to score on one: a pool file can be
renamed or moved, and the same release read as PDF or as a text dump records two
different names. Reading tolerates a file with no header and ignores any `#`
line.

**Bounded question bodies.** A question's body may not run past the start of
another question header. Without that bound the non-greedy body runs to the next
`~~` it can find, and a header with no body of its own swallows every question
between it and that marker.

This is a live defect, not a hypothetical. The Extra pool's errata preamble
carries `E1E10 (C) [97.509(m)]` as a bodyless header; its match runs 8,227
characters and consumes `E1A01`, which is absent from the parsed Extra pool
today. `E1E10` itself survives only because it appears a second time, properly,
and the later parse overwrites the first. Bounding the body recovers `E1A01`,
drops nothing, and leaves Technician and General byte-for-byte unchanged.

**Parse completeness.** Every line that looks like a question header must parse
into a complete question. A header line is `^<ID> (<letter>)`; a complete
question is that header plus a body terminated by `~~`. If any header fails to
yield a question, the script names the offending IDs and exits without running
an exam.

This exists because the parser's failure mode is silent under-reading, not
crashing. An evince copy-paste of the Extra pool yields 542 of 599 questions
while still covering all 50 groups, so it produces a full-length exam drawn from
a pool missing 9% of its questions, with nothing to notice. The check converts
that into a refusal.

The pool's own `SUBELEMENT ... NN Questions` declarations are **not** used. They
state pre-errata counts, and the errata prose does not reconcile with them: the
General pool declares 425, withdraws 9 by errata, and contains 423. A check
built on those numbers would refuse a sound pool.

**Scoring.** Scoring runs at the end of an exam, and can also run against a
saved answers file without re-taking the exam. The report gives the score,
pass/fail against `ceil(0.74 x exam length)`, a per-subelement breakdown, and
each missed question with the correct answer.

**Documentation.** A `README.md` states what the script does, that the pool file
must be supplied by the reader, that `pdftotext` is required for PDF input, and
that 12 Technician questions depend on figures T-1, T-2 and T-3, which the
reader should have the pool PDF open to consult.

**Command line.** `--pool` and `--score` as file arguments. A bare run prompts
for the pool, which is the only thing it cannot derive. No data on stdin or
stdout.

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
9. A completed exam writes `technician_answers_*.txt`, `general_answers_*.txt`
   or `extra_answers_*.txt` according to the pool it was drawn from.
10. That file opens with `# pool: <the pool's own filename>`, and `--score`
    prints it next to the pool being scored against. A file without the header
    still scores.
11. The three `pdftotext` pools in hand parse with zero unparsed headers and
    run normally: Technician 409, General 423, Extra 599.
11a. Technician and General parse to output identical to before the change;
    Extra gains exactly `E1A01` and loses nothing.
11b. No parsed body exceeds roughly 750 characters, the current maximum once
    bodies are bounded. A runaway body is the symptom this guards.
12. The evince copy-paste of the Extra pool is refused: 542 parsed against 564
    header lines, naming at least `E1A05` and `E1D06` among the 22 unparsed,
    and no exam is offered.
13. The refusal names the offending question IDs, not just a count.

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
- Parsing text that a PDF viewer's copy-paste produces. The completeness check
  is what makes this safe to attempt later: a more permissive parser can be
  tried without the risk that made it a bad idea, because a parse that goes
  wrong is refused rather than silently used. It is real work rather than a
  regex tweak: the evince paste damages the text at least three separate ways,
  welding question IDs onto the end of a previous line at page breaks, dropping
  the newline between the `[reference]` and the question text, and losing or
  joining `~~` terminators. Bounding bodies, which this spec adopts for its own
  reasons, leaves 57 of the paste's questions unrecovered, so the remaining work
  is with the other two defects.

## Assumptions

- The script is named `cramfest.py`, after the repository.
- Exam length equals the pool's group count. Verified against all three pools:
  Technician 409 questions / 35 groups, General 423 / 35, Extra 598 / 50,
  giving the published exam lengths of 35, 35 and 50.
- The pass threshold is `ceil(0.74 x exam length)`, giving 26 of 35 and 37 of
  50, matching the published FCC thresholds.
- Questions are presented in random rather than group order.
- The completeness check detects damage without quantifying it. It counts
  headers that sit at the start of a line, so input whose only damage is welding
  IDs onto previous lines would pass: in the evince paste it flags 22 of the 57
  losses. Detection is the goal; a shortfall of any size is a refusal.
- `.gitignore` needs explicit `!/SPEC.md` and `!/README.md` negations, because
  its deny-all whitelist would otherwise refuse both files. `!/*.md` is not
  used, as it would re-admit the personal study records the whitelist exists to
  exclude.
