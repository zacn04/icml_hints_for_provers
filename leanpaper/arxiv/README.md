# arxiv build

Self-contained source tree for the arXiv replacement (v2, camera-ready).

## Contents

- `main.tex` — paper source. Identical to `../icml2026/main.tex` except
  figure paths are local (`figures/X.pdf`) rather than `../../figures/X.pdf`.
- `main.bbl` — precompiled bibliography. Including this means arXiv does
  not have to rerun bibtex.
- `icml2026.sty`, `icml2026.bst`, `algorithm.sty`, `algorithmic.sty`,
  `fancyhdr.sty` — workshop style files, including the chair-specified
  footer in `\ICML@appearing`.
- `refs.bib` — bibliography source (kept for reference; arXiv builds
  from `main.bbl`).
- `figures/{scaling,ablation,venn_overlap}.pdf` — paper figures.

## Compile

```bash
tectonic main.tex          # or: pdflatex main && bibtex main && pdflatex main && pdflatex main
```

## Upload to arXiv as a replacement

1. Verify `main.pdf` looks correct (compile and eyeball).
2. Use the tarball: `leanpaper/arxiv-v2.tar.gz` (already built; regenerate with
   the `tar czf` command in this directory's git history if needed).
3. Go to <https://arxiv.org/abs/2601.16172> -> "Replace" -> upload the tarball.
4. arXiv will compile the source. If it fails (different pdflatex version),
   fall back to uploading `main.pdf` directly.
