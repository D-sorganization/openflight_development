# Contributing to the Technology Review

This document is written to grow — from its current ~60 pages toward a
textbook-scale reference — and to be edited by many people and agents over time,
eventually published on the AffineDrift site. These conventions exist so that
independent edits compose cleanly instead of colliding.

**Read this before editing any `.tex` file.**

## 1. Repository layout

```
tech-review/
├── main.tex                 # skeleton only: \input lines, nothing else
├── preamble.tex             # packages, styling, macros — shared by all files
├── references.bib           # the single bibliography database
├── build.ps1                # local build (Windows/MiKTeX)
├── CONVENTIONS.md           # this file
├── README.md                # reader-facing summary of the report
├── sections/                # one file per chapter or appendix
│   ├── abstract.tex
│   ├── 01-introduction.tex … 10-design-guidance.tex
│   └── appendix-a-references.tex … appendix-d-patent-compendium.tex
└── research/                # raw research dossiers (provenance, not published)
```

**One chapter per file.** This is the core rule that makes parallel editing safe:
two agents working on different chapters never touch the same file. `main.tex`
holds only `\input` lines, so adding a chapter is a one-line change plus a new
file.

## 2. Adding a chapter or appendix

1. Create `sections/NN-slug.tex` (chapters) or `sections/appendix-X-slug.tex`.
2. Start it with `\chapter{Title}` and `\label{ch:slug}` (or `\label{app:slug}`).
3. Add one `\input{sections/NN-slug.tex}` line to `main.tex` in reading order.
4. Do **not** renumber existing files to make room — numeric prefixes are for
   human sorting only, and gaps are fine. Renaming files breaks concurrent
   branches.

## 3. Labels and cross-references

Always cross-reference by label, never by a literal number ("see Chapter 4" goes
stale the moment a chapter is inserted). Use `\cref{...}`, which supplies the
word ("Chapter 4", "Section 4.2") automatically.

| Prefix | Used for | Example |
|--------|----------|---------|
| `ch:` | chapters | `\label{ch:radar}` |
| `app:` | appendices | `\label{app:patents}` |
| `sec:` | sections and subsections | `\label{sec:radarspin}` |
| `eq:` | equations | `\label{eq:sidebands}` |
| `tab:` | tables | `\label{tab:hierarchy}` |
| `fig:` | figures | `\label{fig:dplane}` |

Label slugs are descriptive, not positional: `sec:radarspin`, not `sec:4-3-2`.
**Never change an existing label** — other chapters and future web anchors depend
on it. If a label's name becomes misleading, add the better one alongside it.

## 4. Citations and the bibliography

`references.bib` is the single source of truth. Never hand-write a bibliography
entry inside a section file.

**Citation keys**
- Patents: `usNNNNNNN` — the US number without commas, e.g. `us8845442`.
- Everything else: a short lowercase slug, vendor or author first, then topic:
  `trackmanoert`, `tutelmangear`, `an029`, `leach2017`.
- Keys are permanent. Renaming one silently breaks every `\cite` that uses it.

**Every entry needs exactly one `keywords` value** from this list:

| Keyword | Contents |
|---------|----------|
| `literature` | Peer-reviewed papers, books, conference proceedings |
| `patent` | Patents, portfolio indexes, IP and litigation records |
| `vendor` | Manufacturer technical documentation and product literature |
| `hardware` | Datasheets, application notes, protocols, standards, FCC filings |
| `community` | Independent testing, engineering references, forums, open-source projects |

The printed bibliography is assembled from five keyword-filtered blocks in
`main.tex`, so **an entry with no keyword — or a typo'd one — silently vanishes
from the document.** After adding entries, confirm the counts match:

```bash
grep -c '^@' references.bib && grep -c '\\entry{' main.bbl
```

**Web sources** need `url` and `urldate`. Prefer a DOI when one exists. Append
new entries to the end of their keyword section so concurrent additions don't
conflict in the same lines.

## 5. Prose style

- **One sentence per line.** Start each sentence on a new line and let it run
  long rather than hard-wrapping mid-sentence. Diffs then show which *sentence*
  changed instead of a reflowed paragraph, which makes review and merge far
  cleaner. (Older text predates this rule; convert paragraphs to
  sentence-per-line as you edit them, but don't reflow files you aren't
  otherwise touching — that creates noise diffs.)
- Write in full sentences and define terms on first use. This is a reference
  document that people will read out of order.
- Use the parameter definitions and coordinate conventions fixed in
  `02-parameters.tex` (TrackMan conventions). Do not introduce a competing
  convention in a later chapter.
- Tag every reported quantity as **measured**, **derived**, or **estimated**
  when discussing what a system produces — this distinction is the spine of the
  whole document (see `\cref{tab:hierarchy}`).
- Units go through `siunitx` (`\SI{24}{\giga\hertz}`) or the shorthand macros
  below. American spelling.

## 6. Available macros

Defined in `preamble.tex` — use these instead of ad-hoc formatting:

| Macro | Purpose |
|-------|---------|
| `\patent{US8845442B2}` | Patent number that hyperlinks to Google Patents |
| `\degs` | Degree symbol (`\si{\degree}`) |
| `\mph`, `\rpm` | Speed and spin units with correct spacing |
| `\vect{v}` | Bold vector |
| `\uvec{n}` | Unit vector (hat + bold) |
| `\begin{implication}…\end{implication}` | Green callout: a consequence an implementer must act on |
| `\begin{keypoint}…\end{keypoint}` | Blue callout: a load-bearing conclusion |
| `\begin{warning}…\end{warning}` | Red callout: a claim that is wrong, contested, or untraceable |

### Neutrality

This document is vendor- and project-neutral. Name a product only as
**evidence** — a published definition, a measured tolerance, a patent claim —
never as a design target or an endorsement. Write guidance for "an
implementer" or "a radar-first system", not for any particular project. If a
section can only be written by assuming one specific architecture, it belongs
in Chapter 10 as a capability tier, not in the body chapters.

Add new macros to `preamble.tex`, never inline in a section. Watch for name
collisions with loaded packages: `\unit` was already claimed by `siunitx`, which
is why the unit-vector macro is `\uvec`.

## 7. Evidence standard

Every substantive technical claim must be traceable to either:
1. a `\cite` to an entry in `references.bib`, or
2. a source URL recorded in the matching dossier under `research/`.

When new research is done, archive the raw dossier in `research/` in the same
pass that adds the prose. Distinguish clearly between what a source *states*,
what is *measured* in published testing, and what is *inferred* in this
document — vendor marketing routinely blurs the measured/derived boundary and
the report's value depends on not repeating that.

## 8. Building

**Locally (Windows/MiKTeX):**

```bash
pwsh tech-review/build.ps1
```

**Locally (TeX Live / Linux / macOS):**

```bash
cd tech-review && latexmk -pdf main.tex
```

`latexmk` runs biber automatically. The manual sequence is
pdflatex → biber → pdflatex → pdflatex; a single pass will show `[?]` citation
marks and a stale table of contents.

**Verify with the same flags CI uses, and check the exit code.** CI passes
`-halt-on-error`. Without it, pdflatex recovers from a fatal error, continues,
and still emits a PDF — so a log-grep for error strings can come back clean on a
build that CI will reject. Check `$LASTEXITCODE` (or `$?`) rather than trusting
a grep:

```bash
pdflatex -halt-on-error -file-line-error -interaction=nonstopmode main.tex
```

Two failure modes worth knowing. An **undefined colour or macro** only surfaces
where it is *used*, which may be a chapter away from the definition you edited —
rename theme colours across `preamble.tex` *and* every `sections/*.tex` in the
same commit. And on Windows, an **open PDF viewer file-locks `main.pdf`**, which
makes pdflatex fail with "I can't write on file" and leaves a stale PDF in
place; build with `-jobname=verify` to check without touching the locked file.

**In CI:** `.github/workflows/tech-review.yml` compiles the document on every
push and pull request that touches `tech-review/`, fails on LaTeX errors and on
undefined citations or references, and uploads the built PDF as a workflow
artifact. If you cannot build locally, open a pull request and read the CI log —
that is the authoritative check.

**Do not commit build artifacts.** `.aux`, `.bbl`, `.bcf`, `.log`, `.out`,
`.toc`, `.run.xml`, `.fdb_latexmk` and `.fls` are gitignored. (`main.pdf` is
currently still tracked for convenience; once the document is published from the
AffineDrift site it should be dropped from version control and taken from the CI
artifact instead, since a binary that changes on every edit is a guaranteed
merge conflict between parallel contributors.)

## 9. Growth path

Planned evolution, recorded here so contributors build in a compatible direction:

- **Document class.** When the chapter count outgrows a flat `sections/`
  directory, switch `report` to `book` and group chapters under `\part`
  divisions with per-part subdirectories. Stable labels (§3) make this
  mechanical.
- **Web publication.** LaTeX stays canonical. The AffineDrift site will be fed
  by a CI-generated HTML rendition (`make4ht` or LaTeXML — both handle this
  document's math, tables, and hyperlinks). Two consequences for authors: keep
  math in real LaTeX environments rather than images, and keep tables
  semantically simple so they convert well.
- **Splitting.** If a chapter passes roughly 25 pages, split it into a
  subdirectory of `\input` fragments rather than letting one file grow
  unbounded — long files are where concurrent edits start colliding again.
