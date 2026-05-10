.PHONY: all clean serve paper paper-clean figures

SRCS = src/wasm/cbd.c src/wasm/fips202.c src/wasm/indcpa.c src/wasm/kem.c \
       src/wasm/ntt.c src/wasm/poly.c src/wasm/polyvec.c src/wasm/randombytes.c \
       src/wasm/reduce.c src/wasm/symmetric-shake.c src/wasm/verify.c \
       src/wasm/benchmark_api.c

EXPORTS = _mlkem_malloc,_mlkem_free,_mlkem_zeroize,_mlkem_keypair,_mlkem_enc,_mlkem_dec
EXPORTS := $(EXPORTS),_sha3_256_wasm,_sha3_512_wasm,_shake256_wasm

RT_METHODS = ccall,cwrap,writeArrayToMemory,getValue,setValue,HEAPU8

EMFLAGS = -O3 -s WASM=1 \
  -s "EXPORTED_RUNTIME_METHODS=[$(RT_METHODS)]" \
  -s "EXPORTED_FUNCTIONS=[$(EXPORTS)]" \
  -s MODULARIZE=1 -s EXPORT_NAME="MLKEMModule" \
  -s ALLOW_MEMORY_GROWTH=1 -s INITIAL_MEMORY=64MB

# ── WASM Build ────────────────────────────────────────────────────────────────
all: dist/mlkem768.js

dist/mlkem768.js: $(SRCS)
	@mkdir -p dist
	emcc $(SRCS) $(EMFLAGS) -o dist/mlkem768.js

# ── Development Server ────────────────────────────────────────────────────────
serve:
	python3 -m http.server 8080

clean:
	rm -f dist/mlkem768.js dist/mlkem768.wasm

# ── Paper Build ───────────────────────────────────────────────────────────────
PAPER    = paper
FIGDIR   = analysis/figures
FIGURES  = $(wildcard $(FIGDIR)/*.pdf)
DATAFILE = $(wildcard performance_data/*.csv)

# Generate all figures from telemetry CSV
figures: $(DATAFILE) analysis/generate_figures.py
	@echo "==> Generating figures from telemetry data..."
	cd analysis && ../.venv/bin/python3 generate_figures.py
	@echo "==> Figures written to $(FIGDIR)/"

# Build paper PDF (runs pdflatex→bibtex→pdflatex×2)
paper: figures $(PAPER).pdf

$(PAPER).pdf: $(PAPER).tex references.bib $(FIGURES)
	pdflatex -interaction=nonstopmode $(PAPER).tex
	bibtex $(PAPER)
	pdflatex -interaction=nonstopmode $(PAPER).tex
	pdflatex -interaction=nonstopmode $(PAPER).tex

paper-clean:
	rm -f $(PAPER).pdf $(PAPER).aux $(PAPER).bbl $(PAPER).blg \
	      $(PAPER).log $(PAPER).out $(PAPER).synctex.gz \
	      $(PAPER).fls $(PAPER).fdb_latexmk
