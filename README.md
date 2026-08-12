# ham test cram fest

Practice an FCC amateur radio license exam from the official question pool.

One script, nothing to pip install. Point it at a question pool and it builds an
exam the way a Volunteer Examiner Coordinator does: one question drawn at random
from each subelement group in the pool.

```
python3 cramfest.py --pool "2026-2030 Technician Pool and Syllabus Public Release Feb 19 2026.pdf"
```

## What it does

| Run | Does |
|---|---|
| `--pool POOL` | sit a full exam |
| `--pool POOL --score FILE` | score a saved answers file again |
| `--pool POOL --weak FILE...` | rank what you keep getting wrong |
| `--pool POOL --drill AREA` | drill one subelement or group |

Every mode needs the pool, and nothing else is required to sit an exam, so a
bare `python3 cramfest.py` asks for the pool and then sits one.

## You supply the question pool

The pool is not included here. Download the current one from the NCVEC and pass
it with `--pool`:

https://ncvec.org/index.php/amateur-question-pools

The Technician, General and Extra pools are each reached through that page's
menu items. Both the released PDF and a plain text dump of one work, though only
a PDF can give you the diagrams.

Because the exam shape is read from the pool rather than hardcoded, the same
script covers all three elements. Technician has 35 subelement groups, so a
Technician exam is 35 questions; point it at another element's pool and you get
that pool's group count. Passing is 74%, rounded up: 26 of 35, or 37 of 50.

## Reading a PDF needs pdftotext

PDF input shells out to `pdftotext`, from **poppler-utils**:

```
sudo apt install poppler-utils              # Debian, Ubuntu
brew install poppler                        # macOS
winget install -e --id Schard.Poppler       # Windows
```

Without it the script says so and exits.

You can skip installing anything. Open the pool PDF, select all of it, paste it
into a text file, and pass that instead:

```
python3 cramfest.py --pool pasted.txt
```

That works because the parser reads by position rather than by line, so it does
not care which tool rendered the text: a copy-paste out of a PDF viewer yields
the same questions and the same answers as the PDF itself. What you lose is the
diagrams, which are images inside the PDF and cannot survive being pasted as
text.

Use `pdftotext` with no flags. `-layout` also parses, but it disagrees with the
default on one question's wording, so there is no reason to prefer it.

Given a PDF, the script writes the text dump alongside it and reuses it on later
runs, falling back to a temporary file if that directory is not writable.

## Sitting an exam

Questions come one at a time. Answer `A`, `B`, `C` or `D`, or press `q` to
abandon the attempt: nothing is saved and nothing is scored, so treat it as
walking away rather than pausing. There is no resume.

Finish, and your answers are written to the working directory as
`technician_answers_2026-08-12_090145.txt`, named for the element you sat and
when. The report gives your score, pass or fail, a per-subelement breakdown, and
every question you missed with the correct answer.

Each missed question ends with an **Explain this question** link, which searches
the web for that question by its ID. Study sites index the pool that way, so the
results are usually about the exact question rather than the topic at large.

## Diagrams

Some questions refer to a figure: a schematic or chart printed in the pool PDF.
Technician has 3 such figures across 12 questions, General 1 across 5, and Extra
10 across 27.

Where it can, the script turns the reference itself into a link:

```
Question 14/35  [T6C02]
What is component 1 in figure T-1?      <- "figure T-1" is clickable
A. Resistor
B. Transistor
C. Battery
D. Connector
```

Clicking it opens the figure in whatever you use for images. That needs the pool
as a PDF and **tesseract** installed:

```
sudo apt install tesseract-ocr                          # Debian, Ubuntu
brew install tesseract                                  # macOS
winget install -e --id UB-Mannheim.TesseractOCR         # Windows
```

Tesseract reads each figure's caption. The captions are drawn into the images
rather than stored as text, and the figures cannot be told apart by their order:
the Extra pool ships a hidden mask alongside every figure, and its numbering
jumps from E7-3 straight to E9-1. Reading the caption is the only way to know
which image is which, and showing you the wrong schematic would be worse than
showing none.

Without tesseract, or from a text pool, the question says this instead:

```
Refer to PDF for Figure T-1
```

so keep the pool PDF to hand either way. Figures are extracted once and cached
beside the pool, or in a temporary directory if that is not writable.

## Scoring a saved file

```
python3 cramfest.py --pool pool.pdf --score technician_answers_2026-08-12_090145.txt
```

**Score against the same pool you sat.** Not merely the same element: the same
release. A question ID like `T1C01` names a slot in the pool's structure, not a
question for all time, so every four-yearly release reuses the same IDs for
different questions. Score a 2026-2030 Technician attempt against the 2030-2034
pool and every ID resolves, nothing looks wrong, and the result is meaningless.
Using the wrong *element* is safe by comparison, because it fails outright.

So the answers file opens with a line naming the pool it was sat against:

```
# pool: 2026-2030 Technician Pool and Syllabus Public Release Feb 19 2026.pdf
T5C11 A
T0A01 A
```

and `--score` prints that beside the pool you handed it:

```
Answers recorded against: 2026-2030 Technician Pool ... Feb 19 2026.pdf
Scoring against:          2026-2030 Technician Pool ... Feb 19 2026.pdf
```

It reports rather than refuses, because the two can differ innocently: you
renamed the pool, or sat it from the PDF and are scoring from the text dump.
Read the two lines and judge. A file with no header scores normally and reports
its pool as `unrecorded`.

## Where you need to study

Point `--weak` at any number of saved answers files:

```
python3 cramfest.py --pool pool.pdf --weak technician_answers_*.txt
```

```
70 answers over 2 file(s)

By subelement, weakest first
  T1    18.2%   2 of 11 wrong
  T8    15.4%   2 of 13 wrong
  T9    12.5%   1 of 8 wrong
  ...

By group, under the subelement ranking
  T1A   33.3%   1 of 3 wrong
  T1C   50.0%   1 of 2 wrong
  T8A  100.0%   1 of 1 wrong
  ...

By group, weakest first
  T8A  100.0%   1 of 1 wrong
  T1C   50.0%   1 of 2 wrong
  T1A   33.3%   1 of 3 wrong
  ...
```

The counts sit beside every percentage because they matter: `1 of 1 wrong` is
100% and means almost nothing, while `2 of 13` is a real signal.

The missed groups appear twice on purpose. Ranked on their own, they tell you
what to study next. Laid out under the subelement ranking, the two tables line
up, so you can see which groups made a subelement weak. Both list only groups
you have missed at least once.

Files are scored against the pool you pass, so anything not in it — an older
release, a different element — is listed as uncounted rather than folded into
the numbers.

## Drilling one area

`--weak` tells you what to study; `--drill` studies it. Pass a subelement or a
group and it asks every question in it, in random order:

```
python3 cramfest.py --pool pool.pdf --drill T8C     # one group, 11 questions
python3 cramfest.py --pool pool.pdf --drill T8      # one subelement, 47
```

Groups run 8-15 questions and subelements 23-99, so `--count` caps a long one:

```
python3 cramfest.py --pool pool.pdf --drill E7 --count 20
```

A count of nought, or one larger than the area holds, asks the whole area rather
than complaining. Which questions you get is random too, so drilling the same
area twice is not the same drill.

There is no pass mark on a drill: 74% is a threshold for a 35-question exam and
means nothing across twelve questions from one group. You get the score and the
questions you missed.

Answers go to `technician_drill_T8C_<timestamp>.txt`, deliberately not the exam
filename. You drill what you are weak at, so counting drills as exam attempts
would keep those areas looking bad. Glob whichever set you want:

```
python3 cramfest.py --pool pool.pdf --weak technician_answers_*.txt   # exams
python3 cramfest.py --pool pool.pdf --weak technician_drill_*.txt     # drills
```

## On Windows

**Use Windows Terminal, not the old console host.**

Both the figure links and the **Explain this question** links are terminal
hyperlinks. Windows Terminal renders them; the legacy console that `cmd.exe`
opens on older systems does not, and shows the escape characters as junk around
the label instead. Everything still runs, but it is unpleasant to read.

Windows ships no `pdftotext`; poppler there is a third-party build. The
`Schard.Poppler` winget package puts it on `PATH`, which is where the script
looks. Or skip it and paste the pool out of your PDF viewer.

Figure links additionally need `UB-Mannheim.TesseractOCR`. That installer does
not always add itself to `PATH`, so the script also looks in
`C:\Program Files\Tesseract-OCR`.
