# ham test cram fest

Practice an FCC amateur radio license exam from the official question pool.

One script, nothing to pip install. Point it at a question pool and it builds an
exam the way a Volunteer Examiner Coordinator does: one question drawn at random
from each subelement group in the pool.

Reading a PDF needs `pdftotext` on your system, covered below. A text dump of
the pool needs nothing at all.

```
python3 cramfest.py --pool "2026-2030 Technician Pool ... .pdf"
```

## You supply the question pool

The pool is not included here. Download the current one from the NCVEC and pass
it with `--pool`. Both the released PDF and a plain text dump of it work.

https://ncvec.org/index.php/amateur-question-pools

The Technician, General and Extra pools are each reached through that page's
menu items.

Because the exam shape is read from the pool rather than hardcoded, the same
script covers Technician, General and Extra. Technician has 35 subelement
groups, so a Technician exam is 35 questions; point it at another element's
pool and you get that pool's group count.

Passing is 74%, rounded up: 26 of 35, or 37 of 50.

## Reading a PDF needs pdftotext

PDF input shells out to `pdftotext`, from **poppler-utils**:

```
sudo apt install poppler-utils              # Debian, Ubuntu
brew install poppler                        # macOS
winget install -e --id Schard.Poppler       # Windows
```

Without it, the script tells you so and exits.

You can skip installing anything. Open the pool PDF, select all of it, paste it
into a text file, and pass that:

```
python3 cramfest.py --pool pasted.txt
```

That works because the parser reads by position rather than by line, so it does
not care which tool rendered the text. A copy-paste out of a PDF viewer yields
the same questions and the same answers as the PDF itself.

Use `pdftotext` with no flags. `-layout` also parses, but it disagrees with the
default on one question's wording, so there is no reason to prefer it.

When given a PDF, the script writes the text dump alongside it and reuses it on
later runs, falling back to a temporary file if that directory is not writable.

## On Windows

**Use Windows Terminal, not the old console host.**

Each missed question ends with a clickable link to a web search for it. That is
a terminal hyperlink, and Windows Terminal renders it as one. The legacy console
that `cmd.exe` opens on older systems does not, and shows the escape characters
as junk around the label instead. Nothing else depends on it, so the exam still
runs either way, but the report is unpleasant to read.

Windows ships no `pdftotext`; poppler there is a third-party build. The winget
package above puts it on `PATH`, which is where the script looks for it. Or skip
it entirely and paste the pool out of your PDF viewer, as described above.

## Diagrams are not shown

Twelve questions in the Technician pool refer to figures **T-1**, **T-2** and
**T-3**, which are drawings in the pool PDF. The script prints the question text
only; it has no way to draw them, and does not flag which questions need them.

This is not a rare corner. Group T6C is ten-twelfths diagram questions and every
exam draws one question from T6C, so about 86% of Technician exams contain at
least one question you cannot answer from the text alone.

**Keep the pool PDF open beside you** and look up the figures when a question
mentions one.

## Finishing an exam saves it

Complete the exam and your answers are written to the working directory as
`technician_answers_2026-08-11_130945.txt`, named for the element you sat and
when. Press `q` at any question to abandon the attempt: nothing is saved and
nothing is scored, so treat it as walking away rather than pausing. There is no
resume.

Score a saved file later without retaking the exam:

```
python3 cramfest.py --pool pool.pdf --score technician_answers_2026-08-11_130945.txt
```

**Score an answers file against the same pool you sat.** Not merely the same
element: the same release. A question ID like `T1C01` names a slot in the pool's
structure, not a question for all time, so every four-yearly release reuses the
same IDs for different questions. Score a 2026-2030 Technician attempt against
the 2030-2034 pool and every ID resolves, nothing looks wrong, and the result is
meaningless. Scoring against the wrong *element* is safe by comparison, because
it fails outright.

So the answers file opens with a line naming the pool it was sat against:

```
# pool: 2026-2030 Technician Pool and Syllabus Public Release Feb 19 2026.pdf
T5C11 A
T0A01 A
```

`--score` prints that alongside the pool you handed it, so a mismatch is
something you can see:

```
Answers recorded against: 2026-2030 Technician Pool ... Feb 19 2026.pdf
Scoring against:          2026-2030 Technician Pool ... Feb 19 2026.pdf
```

It reports rather than refuses, because the two names can differ innocently —
you renamed the pool, or sat it from the PDF and are scoring from the text dump.
Read the two lines and judge. A file with no header scores normally and reports
its pool as `unrecorded`.

The report gives your score, pass or fail, a per-subelement breakdown, and every
missed question with the correct answer.

Each missed question ends with an **Explain this question** link. Click it and
your browser searches for an explanation of that question. It is a terminal
hyperlink, so it needs a terminal that supports them — most modern ones do, and
those that do not simply show the words without the link.

## Running it bare

Run it with no arguments and it prompts for what it needs, offering a
timestamped answers filename as the default.

```
python3 cramfest.py
```
