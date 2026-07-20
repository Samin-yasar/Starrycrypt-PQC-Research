# =============================================================================
# Makefile — StarryCrypt-PQC Research Artifact
# =============================================================================
#
# OVERVIEW
# --------
# This Makefile manages three build pipelines:
#
#   1. WASM (Emscripten) build  — compiles ML-KEM-768 C sources to WASM/JS.
#   2. Development server       — serves benchmark pages over HTTP.
#   3. Paper build (LaTeX)      — generates figures then builds the PDF.
#
# PREREQUISITES
# -------------
#   WASM build:   emcc (Emscripten SDK 3.1+)   — https://emscripten.org/
#   Paper build:  pdflatex, bibtex             — TeX Live or MiKTeX
#                 python3 + venv at .venv/     — see requirements.txt
#   Dev server:   python3 (stdlib http.server)
#
# QUICK START
# -----------
#   make          # Build WASM (default target)
#   make serve    # Serve on http://localhost:8080
#   make paper    # Generate figures + compile PDF
#   make clean    # Remove WASM build artefacts
#   make paper-clean  # Remove LaTeX auxiliary files
#
# =============================================================================

.PHONY: all clean serve paper paper-clean figures

# ── Source files ─────────────────────────────────────────────────────────────
# PQClean ML-KEM-768 clean reference implementation (FIPS 203).
# Files are compiled together into a single Emscripten output unit; there
# is no separate linking step because all symbols are resolved by emcc.
SRCS = src/wasm/cbd.c         \
       src/wasm/fips202.c     \
       src/wasm/indcpa.c      \
       src/wasm/kem.c         \
       src/wasm/ntt.c         \
       src/wasm/poly.c        \
       src/wasm/polyvec.c     \
       src/wasm/randombytes.c \
       src/wasm/reduce.c      \
       src/wasm/symmetric-shake.c \
       src/wasm/verify.c      \
       src/wasm/benchmark_api.c

# ── WASM Exported Functions ───────────────────────────────────────────────────
# Only the functions listed here are accessible from JavaScript via ccall/cwrap.
# The leading underscore is the C symbol naming convention required by Emscripten.
#
# Core KEM functions (from kem.c / wasm_export.c / benchmark_api.c):
EXPORTS = _mlkem_malloc,_mlkem_free,_mlkem_zeroize
EXPORTS := $(EXPORTS),_mlkem_keypair,_mlkem_enc,_mlkem_dec
# Hash functions (from fips202.c / symmetric-shake.c):
EXPORTS := $(EXPORTS),_sha3_256_wasm,_sha3_512_wasm,_shake256_wasm

# ── Emscripten Runtime Methods ────────────────────────────────────────────────
# These Emscripten runtime helpers are imported by mlkem768-wrapper.js:
#   ccall / cwrap          — call exported C functions with type marshalling
#   writeArrayToMemory     — copy JS Uint8Array → WASM heap
#   getValue / setValue    — read/write WASM heap at a given offset and type
#   HEAPU8                 — direct Uint8Array view of the WASM heap
RT_METHODS = ccall,cwrap,writeArrayToMemory,getValue,setValue,HEAPU8

# ── Emscripten Compilation Flags ──────────────────────────────────────────────
# -O3                    — full optimisation (required for NTT performance)
# WASM=1                 — emit WebAssembly binary, not asm.js
# EXPORTED_RUNTIME_METHODS — allowlist for Emscripten glue helpers (see above)
# EXPORTED_FUNCTIONS     — allowlist for C symbol exports (see above)
# MODULARIZE=1           — emit a factory function instead of running on load;
#                          allows deferred instantiation and multiple instances
# EXPORT_NAME            — name of the factory function set on window object
# ALLOW_MEMORY_GROWTH=1  — allow linear memory to grow beyond INITIAL_MEMORY
#                          (required because key/ct buffers are stack-allocated
#                          per-call but total heap usage grows with parallelism)
# INITIAL_MEMORY=64MB    — starting heap size; must cover:
#                            pk=1184, sk=2400, ct=1088, ss=32 bytes × N calls
#                          64 MB is well above any realistic concurrent use.
EMFLAGS = -O3 -s WASM=1 \
          -s "EXPORTED_RUNTIME_METHODS=[$(RT_METHODS)]" \
          -s "EXPORTED_FUNCTIONS=[$(EXPORTS)]" \
          -s MODULARIZE=1 -s EXPORT_NAME="MLKEMModule" \
          -s ALLOW_MEMORY_GROWTH=1 -s INITIAL_MEMORY=64MB

# =============================================================================
# WASM Build
# =============================================================================

# Default target: build WASM module to dist/
all: dist/mlkem768.js

# dist/mlkem768.js also produces dist/mlkem768.wasm (Emscripten always emits both).
# The JS file is the Emscripten glue (loader + runtime helpers).
# The WASM binary contains the compiled ML-KEM-768 machine code.
dist/mlkem768.js: $(SRCS)
	@mkdir -p dist
	emcc $(SRCS) $(EMFLAGS) -o dist/mlkem768.js
	@echo "WASM build complete: dist/mlkem768.js + dist/mlkem768.wasm"

# =============================================================================
# Development Server
# =============================================================================

# Serves the repository root over HTTP so that browser pages can load
# dist/mlkem768.js and dist/mlkem768.wasm without cross-origin errors.
# (WASM binaries must be served with MIME type application/wasm, which
#  python3 -m http.server handles correctly since Python 3.7.4.)
serve:
	python3 -m http.server 8080

# =============================================================================
# Cleanup
# =============================================================================

# Remove compiled WASM artefacts. Source files and performance_data are
# never removed by this target.
clean:
	rm -f dist/mlkem768.js dist/mlkem768.wasm
	@echo "WASM build artefacts removed."

# =============================================================================
# Paper Build
# =============================================================================

PAPER    = paper
FIGDIR   = analysis/figures
# Figures are only rebuilt when the telemetry CSV or generate_figures.py changes.
FIGURES  = $(wildcard $(FIGDIR)/*.pdf)
DATAFILE = $(wildcard performance_data/*.csv)

# Generate all 8 publication figures from the telemetry CSV.
# Uses the virtual environment at .venv/ which must be provisioned first:
#   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
figures: $(DATAFILE) analysis/generate_figures.py
	@echo "Generating publication figures from telemetry data..."
	cd analysis && ../.venv/bin/python3 generate_figures.py
	@echo "Figures written to $(FIGDIR)/"

# Build the paper PDF.
# LaTeX compilation sequence:
#   1. pdflatex        — first pass: generates .aux with undefined references
#   2. bibtex          — resolves bibliography citations from references.bib
#   3. pdflatex        — second pass: incorporates bibliography
#   4. pdflatex        — third pass: resolves remaining cross-references
# This four-pass sequence is required whenever bibliography entries change.
paper: figures $(PAPER).pdf

$(PAPER).pdf: $(PAPER).tex references.bib $(FIGURES)
	pdflatex -interaction=nonstopmode $(PAPER).tex
	bibtex $(PAPER)
	pdflatex -interaction=nonstopmode $(PAPER).tex
	pdflatex -interaction=nonstopmode $(PAPER).tex

# Remove LaTeX auxiliary files (but NOT the compiled PDF or figures).
# Run `make paper-clean && make paper` for a clean full rebuild.
paper-clean:
	rm -f $(PAPER).aux $(PAPER).bbl $(PAPER).blg \
	      $(PAPER).log $(PAPER).out $(PAPER).synctex.gz \
	      $(PAPER).fls $(PAPER).fdb_latexmk
	@echo "LaTeX auxiliary files removed (PDF preserved)."
