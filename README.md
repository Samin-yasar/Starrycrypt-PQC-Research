# StarryCrypt-PQC


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20111815.svg)](https://doi.org/10.5281/zenodo.20111815)
[![WASM](https://img.shields.io/badge/WebAssembly-✓-654FF0)](https://webassembly.org/)
[![FIPS 203](https://img.shields.io/badge/FIPS%20203-Compliant-green)](https://csrc.nist.gov/projects/post-quantum-cryptography)

**Web-Based Post-Quantum Cryptography: A Statistical Analysis of ML-KEM-768 in Controlled Browser Environments**

This repository contains the implementation, benchmarking harness, and analysis code for the paper *"Evaluating Web-Based Post-Quantum Cryptography: A Statistical Analysis of ML-KEM-768 in Controlled Browser Environments"* (Preprint, 2026).

## Overview

StarryCrypt-PQC implements **ML-KEM-768** (FIPS 203) with **X25519 hybrid key exchange** for web browsers. The implementation is available in both **WebAssembly (WASM)** and **pure JavaScript** variants, enabling comprehensive performance comparison across browser engines and device tiers.

### Key Features

- 🔐 **FIPS 203 Compliant**: NIST-standardized ML-KEM-768 implementation
- 🔄 **Hybrid Key Exchange**: ML-KEM-768 + X25519 with HKDF-SHA-256
- ⚡ **WASM Optimization**: 3.45× observed latency reduction over pure JavaScript
- 📊 **Statistical Rigor**: 462 benchmark sessions across 22 hardware configurations
- 🧪 **Constant-Time Testing**: Browser-native Welch's t-test harness
- 📱 **Cross-Platform**: WebKit, Blink, Gecko support

## Quick Start

### Prerequisites

- [Emscripten](https://emscripten.org/) (for WASM compilation)
- Modern web browser with WebAssembly support
- Python 3.8+ (for data analysis)
- Node.js 18+ (optional, for JS development)

### Installation

```bash
# Clone the repository
git clone https://github.com/Samin-yasar/starrycrypt-pqc.git
cd starrycrypt-pqc

# Build the WASM module
make all

# Serve locally for testing
make serve
# Then open http://localhost:8080/benchmark/
```

### Using the Library

#### WASM Implementation (Recommended)

```javascript
import { loadModule, generateKeypair, encapsulate, decapsulate } from './src/js/mlkem768-wrapper.js';

// Load the WASM module
await loadModule('./dist/mlkem768.js');

// Generate keypair
const { publicKey, secretKey } = await generateKeypair();

// Encapsulate (client side)
const { ciphertext, sharedSecret: ssClient } = await encapsulate(publicKey);

// Decapsulate (server side)
const sharedSecret = await decapsulate(ciphertext, secretKey);

// sharedSecret === ssClient ✓
```

#### Pure JavaScript Implementation

```javascript
import { generateKeypair, encapsulate, decapsulate } from './src/js/purejs-wrapper.js';

// Same API as WASM version
const { publicKey, secretKey } = await generateKeypair();
const { ciphertext, sharedSecret } = await encapsulate(publicKey);
```

## How to Run

### 1. Build the WASM Module

Requires [Emscripten](https://emscripten.org/) installed and activated:

```bash
make all          # compiles src/wasm/*.c → dist/mlkem768.js + dist/mlkem768.wasm
make clean       # removes compiled output
```

### 2. Run the Browser Benchmark

```bash
make serve       # starts python3 HTTP server on port 8080
```

Then open in your browser:
- **WASM benchmark**: `http://localhost:8080/benchmark/`
- **Pure JS benchmark**: `http://localhost:8080/benchmark/pure-js.html`

The benchmark runs automatically and downloads results as JSON.

### 3. Run the Dashboard

Open `http://localhost:8080/dashboard/` (requires `make serve` running).

### 4. Reproduce Paper Figures & Statistics

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib numpy scipy

# Generate figures
cd analysis && python3 generate_figures.py

# Run statistical tests
python3 statistical_tests.py
```

Or use the Makefile (requires an active venv at `.venv/`):

```bash
make figures     # generates figures from telemetry CSV
make paper       # builds paper PDF (pdflatex → bibtex → pdflatex ×2)
```

### 5. Verify Data Integrity

```bash
python3 scripts/verify_data.py
python3 scripts/explore_data.py
```

## Repository Structure

```
starrycrypt-pqc/
├── src/
│   ├── wasm/              # C source for WASM compilation
│   │   ├── kem.c          # ML-KEM-768 core implementation
│   │   ├── fips202.c      # SHA-3/SHAKE (FIPS 202)
│   │   ├── indcpa.c       # IND-CPA secure PKE
│   │   ├── poly.c         # Polynomial arithmetic
│   │   └── ...
│   └── js/                # JavaScript wrappers
│       ├── mlkem768-wrapper.js    # WASM wrapper
│       ├── purejs-wrapper.js      # Pure JS implementation
│       └── telemetry.js          # Benchmarking telemetry
├── dist/                  # Compiled WASM output
│   ├── mlkem768.js
│   └── mlkem768.wasm
├── benchmark/             # Benchmarking harness
│   ├── index.html
│   └── pure-js.html
├── data/                  # Telemetry dataset
│   └── starrycrypt_telemetry_2026-05-05.csv
├── analysis/              # Figure generation
│   ├── figures/           # Generated PDFs/PNGs
│   └── scripts/           # Python analysis scripts
├── docs/                  # Documentation
├── paper/                 # LaTeX paper source
└── Makefile               # Build automation
```

## Benchmarking

### Run Browser Benchmark

1. Build the WASM module: `make all`
2. Start local server: `make serve`
3. Open `http://localhost:8080/benchmark/` in target browser
4. Benchmark runs automatically and downloads results as JSON

### Run Headless Benchmarking

For automated testing across multiple browsers:

```bash
cd scripts/
node run_browserstack.js  # Requires BrowserStack credentials
```

### Reproducing Paper Figures

```bash
# Generate all figures from telemetry data
cd analysis
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install pandas matplotlib numpy scipy

# Generate figures
python3 generate_figures.py

# Run statistical tests (Welch's t-test, Cohen's d, confidence intervals)
python3 statistical_tests.py
```

## Performance Results

| Implementation | Mean Latency | Median | Observed Ratio |
|-----------------|--------------|--------|----------------|
| WASM (all) | 2.34 ms | 1.28 ms | **3.45×** |
| Pure JavaScript | 8.07 ms | 4.37 ms | baseline |

**Key Finding**: WASM delivers 3.45× observed latency reduction over pure JS (2.34 ms vs 8.07 ms; p < 0.0001, survives Bonferroni correction). **Caveat**: ≈87% of total handshake latency is uninstrumented framework overhead; the cryptographic core advantage is 7–9×.

## Constant-Time Testing

The repository includes a browser-native heuristic screening harness based on Welch's t-test:

```javascript
import { runCTTest } from './src/js/telemetry.js';

// Run constant-time test (N=100 interleaved trials)
const result = await runCTTest({ iterations: 100 });
console.log(`t-statistic: ${result.tStat} (|t| < 2.0 suggests no gross leakage)`);
```

**⚠️ Important**: This harness provides *development-stage screening only*. Production deployment requires TVLA-grade evaluation (N ≥ 10,000) with hardware-level timing.

## FIPS 203 Compliance

Our implementation correctly applies all NIST-mandated modifications from Kyber Round 3:

- ✅ **Hash Domain Separation**: Uses `0x06` for SHA-3, `0x1F` for SHAKE
- ✅ **Dimension Parameter Concatenation**: 33-byte hash input (`seed ∥ k`)
- ✅ **FO Transform**: Correct implicit rejection mechanism

## Hybrid Key Exchange

Implements the shared-secret concatenation order from [draft-ietf-tls-ecdhe-mlkem-04](https://datatracker.ietf.org/doc/draft-ietf-tls-ecdhe-mlkem-04/):

```
combinedSS = HKDF-SHA-256(ML-KEM-768 SS ∥ X25519 SS, "hybrid-kex", 32)
```

## Citation

If you use this code or data in your research, please cite:

```bibtex
@software{yasar2026starrycrypt,
  author       = {Yasar, Samin},
  title        = {StarryCrypt-PQC: Web-Based ML-KEM-768 Implementation and Telemetry Dataset},
  month        = may,
  year         = {2026},
  publisher    = {Zenodo},
  version      = {v2.0.1},
  doi          = {10.5281/zenodo.20111815},
  url          = {https://doi.org/10.5281/zenodo.20111815}
}
```

## Telemetry Dataset

The repository includes our complete benchmark dataset (`data/starrycrypt_telemetry_2026-05-05.csv`):

- **462 total sessions**: 240 WASM, 223 pure JS
- **307 lab sessions**: Controlled synthetic runs (BrowserStack)
- **155 field sessions**: Organic user benchmarks
- **22 hardware configurations**: Budget to flagship devices
- **3 browser engines**: WebKit, Blink, Gecko

Data fields: implementation type, latency measurements (total + per-phase), browser info, device tier, WASM capabilities, baseline MIPS.

## Security Considerations

### Memory Zeroization

WASM implementation includes secure memory clearing:

```c
// wasm_export.c
void mlkem_zeroize(void* ptr, size_t len) {
    volatile unsigned char* p = ptr;
    while (len--) *p++ = 0;
}
```

### Side-Channel Resistance

- No secret-dependent branches in core algorithms
- Constant-time Barrett reduction
- Warning: Browser environments have degraded timing resolution (100μs–1ms) due to anti-fingerprinting measures

## Browser Compatibility

| Browser | WASM | SIMD | Threads | Minimum Version |
|---------|------|------|---------|-----------------|
| Chrome | ✓ | ✓ | ✓ | 57+ |
| Firefox | ✓ | ✓ | ✓ | 52+ |
| Safari | ✓ | ✓ | ✗ | 11+ |
| Edge | ✓ | ✓ | ✓ | 16+ |

## Development

### Building from Source

```bash
# Install Emscripten (if not already installed)
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh

# Build StarryCrypt-PQC
cd /path/to/starrycrypt-pqc
make all
```

### Running Tests

```bash
# Verify FIPS 203 compliance test vectors
node tests/verify_vectors.js

# Run canonical data verification
python3 scripts/verify_data.py
```

## Contributing

Contributions welcome! Please open an issue or PR for:
- Bug fixes
- Performance improvements
- Additional test vectors
- Documentation improvements

## License

MIT License - see [LICENSE](LICENSE) file.

## Acknowledgments

- [CRYSTALS-Kyber](https://pq-crystals.org/kyber/) reference implementation
- [NIST Post-Quantum Cryptography Standardization](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [Emscripten](https://emscripten.org/) WebAssembly compiler
- [@noble/post-quantum](https://github.com/paulmillr/noble-post-quantum) for pure JS comparison baseline

## Contact

- **Research**: research@samin-yasar.dev
- **Issues**: [GitHub Issues](https://github.com/Samin-yasar/starrycrypt-pqc/issues)
- **Paper**: Preprint (link TBD)

---

**⚠️ Disclaimer**: This is research code for evaluation and benchmarking. While we follow FIPS 203 specifications, production deployment should undergo additional security audits and formal verification.
