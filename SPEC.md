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

**Parsing.** The pool is read by position, not by line. All whitespace is
collapsed to single spaces first, so nothing depends on where the source put its
newlines; that is what makes the parser indifferent to how the text was
extracted. Reading then passes three gates:

1. **Anchor.** Everything before the first `[TGE]1A01` header that satisfies the
   choice gate is front matter, and is discarded. Errata, syllabus and cover
   pages never reach the parser.
2. **Shape.** A question header is an ID-shaped token, whitespace, a
   parenthesised answer letter, and an optional bracketed rule reference.
   Candidates are found anywhere in the text.
3. **Choices.** A candidate is a question only if `A.`, `B.`, `C.` and `D.`
   follow it in order before the next candidate. Each marker is the first
   occurrence after the previous one, and no whitespace is required around it.

A question runs from its own header to the next candidate header. The choice
gate is what rejects a header with nothing question-shaped after it, which is
how withdrawn-question placeholders and stray errata headers are excluded
without naming them.

No whitespace may be required around a choice marker, in either direction. The
published Extra pool contains `...on VHF and UHF D.A DX spotting system...`,
with no space after the period, and copied text welds the other way, as in
`...of the aircraftB. The amateur station...`.

**Parse completeness.** Every `~~` in the anchored text must close a parsed
question. The check runs after front matter is discarded, on exactly the text
the parser read, so a terminator ahead of the anchor is out of its reach as well
as the parser's.
Terminators are no longer used to delimit anything, but they remain the only
evidence of a question the parser never saw: a header damaged past recognition
is invisible to a header-driven parser, while its terminator is still there. Any
`~~` closing no question is a refusal, named by line number.

A `~~` legitimately closes nothing where the pool says so in words, beside a
`<ID> Question Deleted (section not renumbered)` placeholder or the end-of-pool
marker. Both are excluded by the text next to them, so the rule needs no
per-pool baseline.

**Scoring.** Scoring runs at the end of an exam, and can also run against a
saved answers file without re-taking the exam. The report gives the score,
pass/fail against `ceil(0.74 x exam length)`, a per-subelement breakdown, and
each missed question with the correct answer.

Every missed question carries a link to a web search for an explanation of it.
The query is the question sentence alone, with its answer choices dropped, since
the choices are noise a search engine matches badly. The link is an OSC 8
terminal hyperlink, so the line reads as its label rather than as a URL;
terminals that do not understand OSC 8 print the label alone and lose nothing
but the link. Correct answers get no link.

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
11. The three `pdftotext` pools parse to Technician 409, General 423, Extra 599,
    with the same IDs, answers and references as the parser they replace.
11a. Technician and General parse to output identical to before the change;
    Extra gains exactly `E1A01` and loses nothing.
11b. No parsed body exceeds roughly 750 characters, the current maximum. A
    question runs to the next header, so a runaway body means a header was
    missed, and length is the cheapest way to see that.
12. A copy-paste of the Extra pool taken from a PDF viewer parses to the same
    599 questions and the same answers as its PDF.
12a. A pool whose body does not open with a usable `[TGE]1A01` is refused.
12b. Front matter yields no questions: no header before the anchor is parsed.
13. A stranded `~~` is refused, naming its line.
14. Each missed question is followed by exactly one search hyperlink, and a
    correctly answered question by none.
15. The search query is the question sentence with no answer choices in it, for
    every question in all three pools.

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

- **The pool body opens with `[TGE]1A01`.** This is the anchor that discards
  front matter, and it is the load-bearing assumption of the whole parser. True
  of the Technician, General and Extra pools in hand. It would break if question
  01 of group 1A were ever withdrawn; withdrawals do happen, `G1A04`, `G1C09`
  and `G8C01` among them, so this is unobserved rather than impossible. A pool
  with no usable anchor is refused rather than parsed unanchored, because the
  alternative is a silently wrong pool.
- Collapsing whitespace discards the line breaks the PDF used inside a question.
  Bodies keep their words, choices and answers, and lose the source's wrapping:
  353 of Technician's 409 bodies are unchanged and 56 differ only in where the
  newlines fall.

- The script is named `cramfest.py`, after the repository.
- Exam length equals the pool's group count. Verified against all three pools:
  Technician 409 questions / 35 groups, General 423 / 35, Extra 599 / 50,
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
