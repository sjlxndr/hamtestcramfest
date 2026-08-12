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
5. **"Self-contained script" vs. questions that require a diagram.** Group T6C
   is 10/12 diagram-dependent and every exam draws from T6C, so 86% of
   Technician exams contain one; Extra has 27 such questions against
   Technician's 12. Resolved by linking the figure rather than drawing it: the
   script extracts the images from the pool PDF, identifies each by reading its
   caption, and offers a link beside the question. Where that is impossible, a
   text pool or a machine without tesseract, the question is asked without a
   figure and the reader falls back to the pool PDF, which the README says to
   keep open.

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

**Text handling.** Every file is read and written as UTF-8, named as a codec
rather than inherited from the locale, because that is what `pdftotext` writes
and a machine whose locale says otherwise would fail on a sound pool. Bytes that
do not decode become replacement characters, and stdout and stderr are set to
replace what they cannot encode. A mangled question still lets the reader sit
the exam; a traceback does not.

**Extraction-independent.** Any faithful text rendering of the pool is accepted:
`pdftotext` output, or text copied out of a PDF viewer. Both yield the same
questions and the same answers, because the parser depends on no property that
differs between them.

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

A question runs from its own header to the next candidate header, and its
content ends at the first `~~` inside that stretch, or at the next header when
there is none. The terminator is not a delimiter and nothing counts terminators,
but without the trim the last choice absorbs it along with any page furniture
sitting between two questions.

The choice gate is what rejects a header with nothing question-shaped after it,
which is how withdrawn-question placeholders and stray errata headers are
excluded without naming them.

No whitespace may be required around a choice marker, in either direction. The
published Extra pool contains `...on VHF and UHF D.A DX spotting system...`,
with no space after the period, and copied text welds the other way, as in
`...of the aircraftB. The amateur station...`.

**Figures.** Where a question names the figure it needs, those words are a link
to the figure's image: the reader clicks the phrase the question already uses,
rather than a line appended beneath it. This applies both when the question is
asked and where it is listed again among the missed questions at the end. The link is an OSC 8 hyperlink to a `file://`
URL, the same mechanism as the search link on a missed question, so it opens in
whatever the reader's system uses for images and nothing steals focus mid-exam.

Figures are extracted once per pool and cached beside it, falling back to a
temporary directory when that location is not writable, as the text dump does.
Extraction is `pdfimages`, which ships in poppler-utils alongside `pdftotext`,
so PDF input gains no new prerequisite. `pdfimages -list` is read first to
learn which extracted files are images and which are soft masks: the Extra pool
ships a mask for every figure, so its twenty files hold ten figures, and taking
them positionally would hand the reader a mask.

**Figures are identified by reading their captions, never by position.** Each
image carries its own caption as pixels; the figure pages hold no extractable
text at all. Tesseract reads the caption, and the label it finds is what maps
the file to the question. Position is not a fallback: Extra numbers its figures
E5-1, E6-1 through E6-3, E7-1 through E7-3, then jumps to E9-1, so nothing about
the sequence is derivable, and a wrong figure shown confidently is worse than no
figure at all.

An image that the default segmentation mode cannot read is retried once with
`--psm 11`, per image rather than as a second pass over all of them. Thirteen of
the fourteen figures across the three pools read first time; only E9-3's small
Smith chart needs the retry, and Technician and General never reach it. The
retry earns its place because the two modes fail on different images: `--psm 11`
alone would lose E6-3.

**A figure that cannot be linked is named instead, never guessed.** Where the
question refers to a figure the script cannot offer, the reference is left as
written and a line reading `Refer to PDF for Figure T-1` follows the question. The question always states which figure it
wants, so the reader can be told exactly what to look up even when the image
itself is unavailable.

This is decided per figure, not per run. A pool whose captions mostly read gives
links for those and the fallback line for the rest, within the same exam. The
whole-run cases fall out of the same rule: a text pool has no images, and a
machine without tesseract cannot identify what it extracted, so every affected
question gets the fallback line.

**Scoring.** Scoring runs at the end of an exam, and can also run against a
saved answers file without re-taking the exam. The report gives the score,
pass/fail against `ceil(0.74 x exam length)`, a per-subelement breakdown, and
each missed question with the correct answer.

Every missed question carries a link to a web search for an explanation of it.
The query is the question ID followed by the question sentence, with the answer
choices dropped, since the choices are noise a search engine matches badly. The
ID leads because study sites index the pool by it, which finds material on that
exact question rather than the topic at large, and is what keeps the link useful
on a diagram question when no figure link is available. The link is an OSC 8
terminal hyperlink, so the line reads as its label rather than as a URL;
terminals that do not understand OSC 8 print the label alone and lose nothing
but the link. Correct answers get no link.

**Documentation.** A `README.md` states what the script does, that the pool file
must be supplied by the reader, that `pdftotext` is required for PDF input, and
that questions depending on a figure are linked to it when the pool is a PDF and
tesseract is installed, and that the reader should otherwise keep the pool PDF
open to consult figures directly.

**Weak areas.** Given a set of answers files, the script reports where study is
needed, ranked worst first. Subelements are listed with the share answered
wrongly and the counts behind it, and under each, the groups within it that were
missed. The counts are shown beside every percentage, so a rate resting on two
answers is visible as such without needing to be flagged.

A report covers one exam element. Answers files name their element in every
question ID, so the element is read from the answers rather than asked for, and
a set spanning more than one is refused rather than combined.

Subelements and groups are named by their codes alone, `T8` and `T8C`. The pool's
own headings would supply titles, but they are not uniform enough to parse
reliably and the codes are what the reader looks things up by.

**Failure.** No user mistake produces a traceback. A pool that does not exist,
cannot be read, or is a directory; an answers file that is not there; a
conversion that fails: each prints one line naming the problem and exits
non-zero.

**Command line.** `--pool` and `--score` as file arguments, and `--weak` taking
one or more answers files. A bare run prompts for the pool, which is the only
thing it cannot derive. No data on stdin or stdout.

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
8. `README.md` names the `pdftotext` prerequisite, the tesseract prerequisite
   for figure links, and what happens without either.
9. A completed exam writes `technician_answers_*.txt`, `general_answers_*.txt`
   or `extra_answers_*.txt` according to the pool it was drawn from.
10. That file opens with `# pool: <the pool's own filename>`, and `--score`
    prints it next to the pool being scored against. A file without the header
    still scores.
11. The three `pdftotext` pools parse to Technician 409, General 423, Extra 599,
    with the same IDs, answers and references as the parser they replace.
11a. On those three pools, no question is gained or lost against the parser
    being replaced, and no answer letter or rule reference changes. Bodies
    differ only in where their newlines fall, never in their words.
11b. No body ends with a `~~`, and none contains text belonging to the next
    question. A question's content stops at its terminator.
12. A copy-paste of the Extra pool taken from a PDF viewer parses to the same
    599 questions and the same answers as its PDF.
12a. A pool whose body does not open with a usable `[TGE]1A01` is refused.
12b. Front matter yields no questions: no header before the anchor is parsed.
13. Each missed question is followed by exactly one search hyperlink, and a
    correctly answered question by none.
14. The search query is the question sentence with no answer choices in it, for
    every question in all three pools.
15. Every figure in all three pools is extracted and identified by its caption:
    Technician `T-1` to `T-3`, General `G7-1`, Extra `E5-1` through `E9-3`,
    fourteen in total, none unread.
16. Every question referring to a figure links that figure's file from the
    words naming it: 12 questions in Technician, 5 in General, 27 in Extra.
16a. A missed question referring to a figure carries the same link where the
    report lists it.
17. Soft masks are never offered as figures. Extra yields twenty extracted
    files and exactly ten figures.
18. A figure that cannot be linked prints `Refer to PDF for Figure <name>`
    instead, naming the figure the question asked for.
19. Links and fallback lines may mix within one exam, decided per figure.
20. A text pool, and a machine without tesseract, produce the fallback line for
    every affected question and no error.
21. A pool path that does not exist, is unreadable, or is a directory prints
    one line and exits 1. So does a missing answers file. No traceback reaches
    the reader.
22. A weak-areas report over the three answers files in hand ranks subelements
    worst first, with the fraction shown beside each percentage, and lists the
    missed groups beneath each subelement.
23. A set of answers files spanning more than one element is refused, naming
    the elements found.
24. Questions in an answers file that are absent from the pool are reported
    rather than counted, so scoring against the wrong release is visible.

## Out of scope

- Drawing a figure in the terminal. Sixel, the kitty protocol and iTerm2's are
  each terminal-specific, detection is unreliable, and Windows terminals
  largely support none of them. The figure is offered as a link and opened by
  whatever the reader already uses for images.
- Any GUI, web interface, or TUI beyond line-by-line prompts.
- Resuming an interrupted exam. Quitting discards the attempt, and the answers
  file is deliberately not a checkpoint.
- Spaced repetition, or weighting an exam toward previously missed questions.
  Reading past attempts to say where study is needed is in scope; changing what
  the next exam asks on that basis is not.
- Shuffling or renaming answer choices.
- Validating or correcting the pool beyond parsing it.
- Reproducing the existing per-subelement study quizzes.

## Deferred

- A study mode that drills a single subelement rather than a full exam.
- A seed argument for reproducible exams.

## Assumptions

- A weak-areas report is read from answers files alone. Nothing is recorded
  between runs beyond those files, so the set the reader passes is the whole
  history the report knows about.
- Figure captions are rendered into the images and are legible to OCR. True of
  all fourteen figures in the three pools in hand: thirteen on the first
  attempt, one on the retry, about two seconds per pool, once, cached after.
- Character handling never raises. Correctness of the displayed text is
  secondary to the exam running: 312 bytes of the Technician pool are curly
  quotes and en-dashes, none of which the parser needs, so degrading them costs
  nothing structural.
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
- Bodies from a viewer copy-paste can differ from the PDF's in wording as well
  as wrapping: ten of Extra's 599 do. Question IDs, answers and rule references
  are identical, so scoring is unaffected; only the display text of those ten
  varies.
- Nothing verifies that the parser read every question the pool contains. A pool
  whose headers are damaged past recognition parses short and says nothing. This
  is accepted deliberately: the tool is for complete pools, and terminator
  counting was scaffolding for a parser that lost questions on ordinary input.
- `.gitignore` needs explicit `!/SPEC.md` and `!/README.md` negations, because
  its deny-all whitelist would otherwise refuse both files. `!/*.md` is not
  used, as it would re-admit the personal study records the whitelist exists to
  exclude.
