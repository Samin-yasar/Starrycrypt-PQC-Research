IACR Submission Package
=======================

Paper Title: Evaluating Web-Based Post-Quantum Cryptography: A Statistical Analysis of ML-KEM-768 in Controlled Browser Environments

Files Included:
-------------
- main.tex          : Main LaTeX source file
- references.bib    : BibTeX bibliography
- fig1_ct_ttest.pdf : Figure 1 - Constant-time t-test (Appendix A)
- fig2_boxplot_wasm_vs_js.pdf : Figure 2 - WASM vs JS boxplot
- fig3_timing_breakdown.pdf   : Figure 3 - Per-phase timing
- fig5_wasm_capabilities.pdf  : Figure 4 - WASM capabilities
- fig6_browser_engine.pdf     : Figure 5 - Browser engine comparison
- fig8_latency_vs_mips.pdf    : Figure 6 - Latency vs MIPS

Compilation:
------------
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex

Or simply:
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex

Contact: research@samin-yasar.dev
