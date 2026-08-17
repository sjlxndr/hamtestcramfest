# ham test cram fest

Practice an FCC amateur radio license exam on your own machine, from the
official question pool. It builds an exam the way a Volunteer Examiner
Coordinator does: one question drawn at random from each subelement group.

## Start here

Get a question pool, then run it either way. No account, no sign-up.

**1. Get a question pool.** The questions are published free by the NCVEC. On
[their question pool page][pools], open the one for the license you are studying
for and download the pool PDF: the file named as the pool and syllabus, not the
separate diagrams or errata file.

**2a. [Run it in your browser][run].** Nothing to install. Click **Open a pool
file**, choose the PDF you just downloaded, wait a few seconds while it reads,
and take an exam.

To keep your own copy of the page, open [cramfest.html][file] and click the
button just above the file labeled **Download raw file**. Save it anywhere and
double-click it whenever you want it; it is one file and it works the same way.

**2b. Or run it in Python.** Download [cramfest.py][script] the same way, and
point it at the pool:

```
python3 cramfest.py --pool <the file you downloaded>
```

A PDF also needs `pdftotext` installed, which
[At the command line](#at-the-command-line) covers, along with what to do on
Windows. Nothing else is required.

Either way, nothing you do leaves your machine. Your pool is read where you
opened it rather than sent anywhere, and your answers are saved on your own
disk: the browser's downloads folder, or the directory you ran the script from.

[run]: https://sjlxndr.github.io/hamtestcramfest/cramfest.html
[file]: https://github.com/sjlxndr/hamtestcramfest/blob/main/cramfest.html
[script]: https://github.com/sjlxndr/hamtestcramfest/blob/main/cramfest.py
[pools]: https://www.ncvec.org/index.php/amateur-question-pools

## Contents

There are two ways to run it, and they do the same things. The first two
sections are how to get each one going; everything after that is what the tool
does, with a line for each way of asking.

- [Start here](#start-here)
- [In a browser](#in-a-browser)
- [At the command line](#at-the-command-line)
  - [Synopsis](#synopsis)
  - [Reading a PDF needs pdftotext](#reading-a-pdf-needs-pdftotext)
  - [On Windows](#on-windows)
- [The question pool](#the-question-pool)
- [Taking an exam](#taking-an-exam)
- [Scoring a saved file](#scoring-a-saved-file)
- [Where you need to study](#where-you-need-to-study)
- [Drilling one area](#drilling-one-area)
- [Learning as you go](#learning-as-you-go)
- [Diagrams](#diagrams)
- [License](#license)

## In a browser

`cramfest.html` is the whole tool as one web page, driven by buttons. Open it
and pick your pool.

It runs two ways, and they behave alike. [Hosted][run], nothing is downloaded at
all, and the PDF is read on a background thread so the page stays responsive
while it works. Saved to your own disk, it is one self-contained file that opens
by double-clicking and does the same reading on the thread that draws the page.
A pool takes the same few seconds to read either way.

Nothing installs, and nothing of this runs on a server: hosted or saved, the page
is a static file and the work happens in your own browser. There is no
`pdftotext` and no tesseract to install either. The page reads the PDF and its
figures itself, fetching the two libraries that do that from a CDN the first time
it needs them, which is the only thing it wants a network for, and only for a
PDF. Hand it a text dump of the pool instead and it fetches nothing at all:
every mode then runs offline, without the figures, exactly as a text pool does
at the command line.

The answers files it saves are the ones `cramfest.py` reads, so you can take an
exam in the browser and score it at the command line, or the other way round.

Three things belong to the page rather than to the tool:

- **The pool is kept once read**, figures included, so a refresh brings it
  straight back instead of reading it again. Opening another pool replaces it,
  and **Forget the kept pool** clears it. Answers are deliberately not kept that
  way: a finished exam leaves a file, and an unfinished one is discarded.
- **The browser's own Back button walks back through the page** rather than out
  of it: out of a question to the **Menu**, out of a report to the same place.
  Backing out of an exam abandons it and says so. Anything that would really
  leave the page mid-exam, a refresh or closing the tab, asks first.
- **Theme** follows whatever your system is set to. The button cycles it through
  light and dark and back to following the system, and remembers which you chose.

## At the command line

`cramfest.py` is the same tool driven by flags, for anyone who would rather work
that way. It needs Python, and `pdftotext` to read a PDF pool.

### Synopsis

```
cramfest.py --pool <pool>
cramfest.py --pool <pool> --score <answers>
cramfest.py --pool <pool> --weak <answers>...
cramfest.py --pool <pool> --drill <area> [--count <n>]
cramfest.py --pool <pool> --feedback [--drill <area>] [--count <n>]
cramfest.py
```

| Option | Meaning |
|---|---|
| `--pool <pool>` | the question pool: the released PDF, or a text dump of one |
| `--score <answers>` | score a saved answers file again instead of taking an exam |
| `--weak <answers>...` | rank what you keep getting wrong, across any number of files |
| `--drill <area>` | ask every question in a subelement (`T8`) or group (`T8C`) |
| `--count <n>` | with `--drill` or `--feedback`, ask at most that many |
| `--feedback` | work through the pool, told the answer after each question |
| `-h`, `--help` | the same list, from the script |

Every mode needs the pool. Nothing else is required to take an exam, so the bare
form asks for the pool and then takes one.

### Reading a PDF needs pdftotext

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

### On Windows

You need two programs installed alongside Python. Both come from **winget**, the
package installer that ships with Windows 11 and reaches Windows 10 through the
App Installer: the same idea as the Microsoft Store, but typed rather than
clicked.

Open **Windows Terminal** (press Start, type `terminal`, press Enter) and paste
these in, one at a time:

```
winget install -e --id Schard.Poppler
winget install -e --id UB-Mannheim.TesseractOCR
```

Close the terminal and open a new one afterward, so it picks up the newly
installed programs.

| What it gives you | Without it |
|---|---|
| **Poppler** reads the question pool out of the PDF | you must paste the pool into a text file yourself |
| **Tesseract** identifies the diagrams | questions say `Refer to PDF for Figure T-1` instead of linking it |

Neither is required to take an exam. If `winget` is not recognized, your Windows
is too old for it; download poppler and tesseract from their own websites
instead, or skip poppler entirely and paste the pool into a text file, as under
[Reading a PDF needs pdftotext](#reading-a-pdf-needs-pdftotext).

**Use Windows Terminal, not the old black `cmd.exe` window.** The figure links
and the **Explain this question** links are clickable only in a terminal that
supports them. Windows Terminal does; the older console shows them as stray
punctuation around the words instead. Everything still works either way, but the
report is unpleasant to read.

If tesseract was installed somewhere other than `PATH`, the script also looks in
`C:\Program Files\Tesseract-OCR`.

## The question pool

The questions are not included here. You download the pool the NCVEC's question
pool committee publishes, and everything else is read out of it: which element
you are studying, how long an exam is, and what it takes to pass.

- **In a browser**, click **Open a pool file** and choose the file. Once it is
  read, the pool is named in bold on its own line, under the question pool box
  on the menu and under the title everywhere else, giving the element and the
  release as in `General, effective 7/01/2023 – 6/30/2027`. That is taken from
  the pool's own front matter rather than from a filename that may have been
  renamed.
- **At the command line**, pass it with `--pool`. A bare run with no flags asks
  for it, since it is the one thing the script cannot work out for itself.

Download the current pools from the NCVEC:

https://www.ncvec.org/index.php/amateur-question-pools

The Technician, General and Extra pools are each reached through that page's
menu items. Both the released PDF and a plain text dump of one work, though only
a PDF can give you the diagrams.

Because the exam shape is read from the pool rather than hardcoded, the same
tool covers all three elements. Technician has 35 subelement groups, so a
Technician exam is 35 questions; point it at another element's pool and you get
that pool's group count. Passing is 74%, rounded up: 26 of 35, or 37 of 50.

## Taking an exam

An exam is one question drawn at random from each subelement group in the pool,
asked in random order, the way a Volunteer Examiner Coordinator builds one.
Questions come one at a time, and the attempt is scored when you finish.

- **In a browser**, click **Take an exam** and answer by clicking a choice.
  **Stop** abandons the attempt. Your answers file downloads when you finish.
- **At the command line**, run it with just `--pool`. Answer `A`, `B`, `C` or
  `D`, or press `q` to abandon. Your answers file is written to the working
  directory.

Abandoning saves nothing and scores nothing, so treat it as walking away rather
than pausing. There is no resume, in either one.

A finished attempt is saved as `technician_answers_2026-08-12_090145.txt`, named
for the element you took and when. The report gives your score, pass or fail, a
per-subelement breakdown, and every question you missed with the correct answer.

Some questions refer to a diagram, and most exams contain at least one: see
[Diagrams](#diagrams) for how those work.

Each missed question ends with an **Explain this question** link, which searches
the web for that question by its ID. Study sites index the pool that way, so the
results are usually about the exact question rather than the topic at large. The
search asks why the other three choices are wrong as well as why the answer is
right, since knowing what rules them out is most of what makes an answer stick.

## Scoring a saved file

An answers file can be scored again later, without retaking anything. It is the
same file either way, so an exam taken in the browser scores at the command
line, and one taken at the command line scores in the browser.

- **In a browser**, click **Score a saved answers file** and choose it.
- **At the command line**, pass it with `--score`:

```
python3 cramfest.py --pool pool.pdf --score technician_answers_2026-08-12_090145.txt
```

**Score against the same pool you took.** Not merely the same element: the same
release. A question ID like `T1C01` names a slot in the pool's structure, not a
question for all time, so every four-yearly release reuses the same IDs for
different questions. Score a 2026-2030 Technician attempt against the 2030-2034
pool and every ID resolves, nothing looks wrong, and the result is meaningless.
Using the wrong *element* is safe by comparison, because it fails outright.

So the answers file opens with a line naming the pool it was taken against:

```
# pool: 2026-2030 Technician Pool and Syllabus Public Release Feb 19 2026.pdf
T5C11 A
T0A01 A
```

and scoring prints that beside the pool you handed it:

```
Answers recorded against: 2026-2030 Technician Pool ... Feb 19 2026.pdf
Scoring against:          2026-2030 Technician Pool ... Feb 19 2026.pdf
```

It reports rather than refuses, because the two can differ innocently: you
renamed the pool, or took it from the PDF and are scoring from the text dump.
Read the two lines and judge. A file with no header scores normally and reports
its pool as `unrecorded`.

## Where you need to study

Given any number of saved answers files, it ranks what you keep getting wrong,
by subelement and by group, so you know what to drill next.

- **In a browser**, click **Weak areas from answers files** and select as many
  as you like in the file picker.
- **At the command line**, point `--weak` at them:

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

Files are scored against the pool you pass, so anything not in it, an older
release or a different element, is listed as uncounted rather than folded into
the numbers.

## Drilling one area

Where weak areas tell you what to study, a drill studies it: every question in
one subelement or group, in random order, scored at the end.

- **In a browser**, choose an **Area**, optionally a **Count**, and click
  **Drill an area**. The area is a menu of what the pool holds, so there is
  nothing to spell wrong; it wants a subelement or a group chosen rather than
  the whole pool.
- **At the command line**, name the area after `--drill`:

```
python3 cramfest.py --pool pool.pdf --drill T8C     # one group, 11 questions
python3 cramfest.py --pool pool.pdf --drill T8      # one subelement, 47
```

Groups run 8-15 questions and subelements 23-99, so a count caps a long one:

```
python3 cramfest.py --pool pool.pdf --drill E7 --count 20
```

A count of zero, or one larger than the area holds, asks the whole area rather
than complaining. Which questions you get is random too, so drilling the same
area twice is not the same drill.

There is no pass mark on a drill: 74% is a threshold for a 35-question exam and
means nothing across twelve questions from one group. You get the score and the
questions you missed.

Answers go to `technician_drill_T8C_<timestamp>.txt`, deliberately not the exam
filename. You drill what you are weak at, so counting drills as exam attempts
would keep those areas looking bad. That way you can ask for either set:

```
python3 cramfest.py --pool pool.pdf --weak technician_answers_*.txt   # exams
python3 cramfest.py --pool pool.pdf --weak technician_drill_*.txt     # drills
```

## Learning as you go

Studying tells you the answer straight after each question, instead of holding
everything back to the end. Nothing is scored and nothing is written: you saw
each answer as you went, so there is nothing left to report afterward.

- **In a browser**, click **Study with answers**. Beside each question is a
  **Skip to** menu that moves to another subelement or group without going back
  to the menu for it, and an **In pool order** switch. Either one restarts the
  run in the new area or the new order.
- **At the command line**, use `--feedback`, narrowed by the same `--drill` and
  `--count` as a drill. It asks about the order before the first question.

```
python3 cramfest.py --pool pool.pdf --feedback
python3 cramfest.py --pool pool.pdf --feedback --drill T8C
python3 cramfest.py --pool pool.pdf --feedback --drill T8 --count 20
```

```
Ask them in (p)ool order, or (s)huffled? [s]:

Question 1/409  [T2A02]
What is the most common frequency for FM simplex operations in the 2 meter band?
A. 146.520 MHz
...
Your answer (A/B/C/D, or 'q' to stop): B

  Incorrect. A. 146.520 MHz
  Explain this question
```

Shuffled is the default and is what every other mode does. **Pool order** works
through the area the way the pool lays it out, which reads better in an area you
are meeting for the first time, since the pool groups related questions together
on purpose. An exam and a drill are always shuffled, so a repeated one does not
rehearse a sequence.

On its own it works through the **whole pool**, not an exam's 35, so it is
something to dip into rather than finish.

Every question gets the **Explain this question** link, right or wrong, unlike
the end-of-exam report, which links only what you missed. Here you are studying,
and a lucky guess is worth reading about too.

## Diagrams

Some questions refer to a figure: a schematic or chart printed in the pool PDF.
Technician has 3 such figures across 12 questions, General 1 across 5, and Extra
10 across 27. Where it can, the tool turns the reference itself into a link, so
the words the question already uses are what you click.

- **In a browser**, clicking `figure T-1` opens the figure under the question.
  Nothing needs installing: the page pulls the images out of the PDF and reads
  their captions itself.
- **At the command line**, the reference becomes a terminal hyperlink that opens
  the figure in whatever you use for images. That needs the pool as a PDF and
  **tesseract** installed:

```
sudo apt install tesseract-ocr                          # Debian, Ubuntu
brew install tesseract                                  # macOS
winget install -e --id UB-Mannheim.TesseractOCR         # Windows
```

```
Question 14/35  [T6C02]
What is component 1 in figure T-1?      <- "figure T-1" is clickable
A. Resistor
B. Transistor
C. Battery
D. Connector
```

Either way, the captions are what identify the figures. They are drawn into the
images rather than stored as text, and the figures cannot be told apart by their
order: the Extra pool ships a hidden mask alongside every figure, and its
numbering jumps from E7-3 straight to E9-1. Reading the caption is the only way
to know which image is which, and showing you the wrong schematic would be worse
than showing none.

Where a figure cannot be offered, from a text pool or without tesseract, the
question names it instead:

```
Refer to PDF for Figure T-1
```

so keep the pool PDF on hand either way. Reading the captions happens once per
pool rather than once per question: the command line caches the extracted
figures beside the pool, or in a temporary directory if that is not writable,
and the browser keeps them with the pool it remembers.

## License

MIT. See [LICENSE](LICENSE).
