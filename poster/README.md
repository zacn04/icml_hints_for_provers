# Poster

ICML 2026 AI for Math Workshop poster.

- **Size:** 24 in (W) × 36 in (H) portrait (61 × 91 cm). Workshop-specific —
  different from the main ICML conference size.
- **Source:** `poster.tex` (beamerposter, `lmodern` font).
- **Figures:** embedded from `../figures/` as PDFs.

## Compile

```bash
tectonic poster.tex
# or, with a full TeX Live:
pdflatex poster.tex && pdflatex poster.tex
```

Output: `poster.pdf` at the right physical size for printing.

## What's in it

Single frame (a poster is one beamer slide), 2-column body:

| Column | Blocks                                              |
|--------|-----------------------------------------------------|
| Left   | Setup · Scaling figure + table · Diversity ablation |
| Right  | Venn · RL-specific bullets · Per-skeleton · Cross-model · Distributional evidence |

Top: title + author + arXiv QR. Bottom: code URL + GitHub QR.

## Tweak

- Palette: edit the `\definecolor{...}` lines near the top.
- Font scale: `[scale=1.05]` option on `\usepackage{beamerposter}`.
- Block heading style: `\setbeamerfont{block title}{...}` and matching `\setbeamercolor`.
- To swap a figure, drop a new PDF in `../figures/` and rerun.
