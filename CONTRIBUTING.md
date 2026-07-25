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
  %s

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
