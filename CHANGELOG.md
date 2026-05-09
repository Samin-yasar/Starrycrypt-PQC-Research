# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-05-06

### Added
- Complete ML-KEM-768 (FIPS 203) implementation
- Hybrid key exchange: ML-KEM-768 + X25519 with HKDF-SHA-256
- WebAssembly (WASM) optimized build
- Pure JavaScript implementation for comparison
- Browser-native constant-time testing harness (Welch's t-test)
- Comprehensive telemetry system for performance benchmarking
- 462-session benchmark dataset across 22 hardware configurations
- 8 publication-quality figures
- IACR ePrint submission ready

### Performance
- WASM achieves 3.45× observed latency reduction over pure JavaScript (2.34ms vs 8.07ms, outlier excluded)
- SIMD-capable browsers: 2.38ms mean latency
- Mobile devices achieve sub-2.5ms latency with modern browsers

### Security
- Constant-time Barrett reduction
- Secure memory zeroization via WASM
- FIPS 203 compliant domain separation

## [1.0.0] - 2025 (Pre-release)

### Added
- Initial ML-KEM implementation (Kyber Round 3)
- Basic WASM compilation
- Simple benchmarking harness

### Changed
- Migrated from Kyber Round 3 to FIPS 203 final standard

## Future Roadmap

### Planned
- [ ] SIMD128 intrinsics for WASM build
- [ ] Web Workers support for multi-threading
- [ ] Streaming API for large data
- [ ] Additional statistical visualizations
- [ ] Formal verification of constant-time properties

### Under Consideration
- [ ] ML-KEM-512 and ML-KEM-1024 variants
- [ ] ML-DSA (FIPS 204) signature support
- [ ] Integration with Web Crypto API polyfill

---

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
