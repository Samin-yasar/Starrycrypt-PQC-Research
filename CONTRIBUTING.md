# Contributing to StarryCrypt-PQC

Thank you for your interest in this research project. This document provides
guidelines for contributors — whether you are reporting a defect, proposing a
methodological improvement, or submitting a pull request.

---

## Table of Contents

1. [Project Scope](#1-project-scope)
2. [Reporting Issues](#2-reporting-issues)
3. [Development Setup](#3-development-setup)
4. [Branching and Pull Request Workflow](#4-branching-and-pull-request-workflow)
5. [Code Style Guidelines](#5-code-style-guidelines)
6. [Testing and Verification Checklist](#6-testing-and-verification-checklist)
7. [Areas Open for Contribution](#7-areas-open-for-contribution)
8. [Security Vulnerability Disclosure](#8-security-vulnerability-disclosure)
9. [Commit Message Convention](#9-commit-message-convention)
10. [License Agreement](#10-license-agreement)

---

## 1. Project Scope

StarryCrypt-PQC is a **research artifact**, not a production cryptography
library. The primary deliverables are:

- A benchmarked, browser-native implementation of ML-KEM-768 (FIPS 203)
  compiled to WebAssembly via Emscripten.
- A comparable pure-JavaScript implementation using `@noble/post-quantum`.
- A hybrid key exchange construction (X25519MLKEM768).
- A telemetry-driven performance analysis pipeline for the accompanying paper.

Contributions that advance these research goals are welcome. Feature requests
outside this scope (e.g., adding unrelated PQC algorithms, building a
production TLS stack) are out of scope for this repository.

---

## 2. Reporting Issues

Before opening a new issue:

1. Search the [existing issues](https://github.com/Samin-yasar/Starrycrypt-PQC-Research/issues)
   and [discussions](https://github.com/Samin-yasar/Starrycrypt-PQC-Research/discussions)
   to check whether the problem has already been reported.

2. Determine the category:

   | Category | Where to report |
   |----------|----------------|
   | Bug (wrong output, crash, test failure) | GitHub Issue |
   | Performance regression | GitHub Issue with benchmark data |
   | Research methodology concern | GitHub Discussion |
   | Security vulnerability | See §8 — do **not** open a public issue |
   | Question or documentation unclear | GitHub Discussion |

3. For bugs, include:
   - A minimal reproducible example (URL, browser, OS, console output).
   - The exact browser version and OS (use `navigator.userAgent`).
   - Whether you are using the WASM or pure-JS implementation.
   - The output of `selfTest()` from the relevant wrapper.

---

## 3. Development Setup

### 3.1 Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Emscripten SDK (`emcc`) | 3.1+ | Compiling C sources to WASM |
| Python | 3.8+ | Analysis scripts and dev server |
| TeX Live / MiKTeX | Current | Paper PDF build |
| Node.js | 18+ | Optional: running local lint tools |

### 3.2 Clone and Build

```bash
git clone https://github.com/Samin-yasar/Starrycrypt-PQC-Research.git
cd Starrycrypt-PQC-Research

# Activate the Emscripten SDK (adjust path to your emsdk installation)
source /path/to/emsdk/emsdk_env.sh

# Build the WASM module
make all

# Serve locally (http://localhost:8080)
make serve
```

### 3.3 Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Verify the analysis pipeline
python3 scripts/verify_data.py
```

### 3.4 Paper Build

```bash
# Generate figures from telemetry CSV
make figures

# Build the full PDF (requires pdflatex + bibtex)
make paper
```

---

## 4. Branching and Pull Request Workflow

1. **Fork** the repository to your own GitHub account.

2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/your-descriptive-name
   ```
   Branch naming convention:
   - `feat/`  — new feature or capability
   - `fix/`   — bug fix
   - `docs/`  — documentation only
   - `perf/`  — performance improvement
   - `refactor/` — code restructuring without behaviour change
   - `analysis/` — changes to analysis scripts or figures

3. **Make changes** following the code style guidelines in §5.

4. **Run the verification checklist** in §6.

5. **Commit** following the convention in §9.

6. **Push** your branch and open a Pull Request:
   - Title: concise imperative description (e.g. `fix: correct Safari SIMD detection edge case`).
   - Description: what changed, why, and how to test it.
   - If the PR fixes a filed issue, add `Closes #<issue>` in the description.

7. Address review feedback; all CI checks must pass before merge.

---

## 5. Code Style Guidelines

### 5.1 C (WASM Sources — `src/wasm/`)

- Follow the Linux kernel coding style (K&R braces, 8-space tab indentation).
- Keep lines under 80 characters.
- Every function must have a Doxygen-style block comment (`/** ... */`)
  documenting its purpose, parameters, return value, and any security notes.
- Comment all non-obvious cryptographic operations with a reference to the
  relevant FIPS 203 / PQClean section.
- Do not introduce undefined behaviour (use `uint8_t`, `uint32_t`, etc.
  from `<stdint.h>` rather than `int` for cryptographic data).

### 5.2 JavaScript (`src/js/`)

- Use ES2020+ features (optional chaining, nullish coalescing, async/await).
- 4-space indentation; no tabs.
- Every exported function must have a JSDoc block with `@param`, `@returns`,
  `@throws`, and a security note where applicable.
- Prefer named constants over magic numbers (e.g. `MLKEM_PUBLICKEYBYTES`
  rather than `1184`).
- Secret material (`sk`, `ss`) must be zeroized with `.fill(0)` before
  releasing the variable.

### 5.3 Python (Analysis Scripts)

- Follow [PEP 8](https://peps.python.org/pep-0008/) strictly (use `flake8`).
- Every module must begin with a module-level docstring explaining its
  purpose, usage, inputs, outputs, and dependencies.
- Every function must have a Google-style or NumPy-style docstring with
  `Args:`, `Returns:`, and `Raises:` sections.
- Use type hints (`def stats(vals: list[float]) -> tuple`) for all public functions.
- Use `#!/usr/bin/env python3` as the shebang on all executable scripts.

### 5.4 Markdown (Documentation)

- Use ATX-style headers (`#`, `##`, `###`).
- Keep prose lines at 80 characters.
- All code samples must specify a language fence (` ```bash `, ` ```python `, etc.).
- Mathematical expressions use LaTeX inline notation where supported
  (e.g. in README sections rendered by GitHub).

---

## 6. Testing and Verification Checklist

Before opening a Pull Request, confirm all of the following:

```
[ ] make all         — WASM build succeeds with no warnings
[ ] make serve       — Local server starts; benchmark pages load without errors
[ ] selfTest()       — Browser console: all checks pass (passed: true)
[ ] verifyConstantTimeRejection() — |t| < 2.0 on both WASM and pure-JS paths
[ ] python3 scripts/verify_data.py — All statistics match verification_report.md
[ ] python3 analysis/statistical_tests.py — Output matches reported values
[ ] flake8 analysis/ scripts/ — No PEP 8 violations
[ ] make figures     — All 8 figures generate without errors or warnings
[ ] make paper       — PDF compiles cleanly (no undefined references)
```

If a check fails, investigate and resolve before submitting the PR. If a
check is intentionally skipped (e.g. paper build with no LaTeX installation),
note this explicitly in the PR description.

---

## 7. Areas Open for Contribution

The following areas are actively seeking contributions:

| Area | Description | Skill Required |
|------|-------------|----------------|
| WASM SIMD optimizations | Emscripten SIMD128 intrinsics for NTT | C, Emscripten |
| Web Workers support | Parallel benchmark execution via SharedArrayBuffer | JavaScript |
| ML-KEM-512 / 1024 variants | Additional FIPS 203 security levels | C |
| Additional test vectors | KAT vectors from NIST FIPS 203 Annex A | C, JavaScript |
| Statistical analysis improvements | Bayesian latency modelling, Shapiro-Wilk normality testing | Python, Statistics |
| Visualization improvements | Interactive figures (D3.js or Vega-Lite) | JavaScript |
| ML-DSA (FIPS 204) | Digital signature companion implementation | C |
| Cross-browser CI | Automated Playwright/Puppeteer benchmark regression tests | JavaScript |

---

## 8. Security Vulnerability Disclosure

If you discover a security vulnerability — including timing side-channels
in the ML-KEM implementation, heap overflow in WASM memory management, or
weaknesses in the HKDF or AES-GCM integration — please follow responsible
disclosure:

1. **Do NOT open a public GitHub issue.**
2. Email `research@samin-yasar.dev` with:
   - A clear subject line: `[SECURITY] StarryCrypt-PQC — <brief description>`
   - A description of the vulnerability and its potential impact.
   - Steps to reproduce or a proof-of-concept (if available).
   - Your preferred disclosure timeline.
3. You will receive an acknowledgement within 72 hours.
4. A fix will be coordinated with you before any public disclosure.

For the avoidance of doubt: the Welch t-test harness in
`verifyConstantTimeRejection()` provides **developmental screening only** and
is not a formal TVLA evaluation. Reports of timing differences detected by
this harness are welcome and should be filed as issues, not security reports,
unless you believe the leakage is practically exploitable.

---

## 9. Commit Message Convention

This project uses the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
specification.

Format:
```
<type>(<scope>): <short summary>

[optional body]

[optional footer: Closes #<issue>, Co-authored-by: ...]
```

Types:
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation change only
- `perf` — performance improvement
- `refactor` — code change that neither fixes a bug nor adds a feature
- `test` — adding or updating tests/verification scripts
- `build` — changes to the Makefile, Emscripten flags, or Python environment
- `analysis` — changes to analysis scripts or figures only

Examples:
```
feat(wasm): add SIMD128 intrinsics for NTT butterfly operations
fix(js): zeroize x25519 shared secret before returning from x25519Derive
docs(api): add JSDoc for verifyConstantTimeRejection parameters
analysis(figures): fix log scale on fig2 y-axis tick labels
```

---

## 10. License Agreement

By submitting a pull request, you agree that your contribution will be
licensed under the [Apache License 2.0](LICENSE), which governs this
repository. You represent that you have the right to license your
contribution under these terms.

If your contribution includes any material derived from PQClean, you confirm
that it remains subject to the public-domain / CC0 terms under which PQClean
is distributed.
