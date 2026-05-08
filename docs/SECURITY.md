# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

📧 **research@samin-yasar.dev**

Please include:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact assessment
- Suggested fix (if you have one)

We aim to respond within 48 hours and will work with you to assess and address the issue.

## Security Considerations

### Browser Environment Limitations

This implementation runs in web browsers which have specific security constraints:

1. **Timing Resolution**: Browsers degrade `performance.now()` to 100μs–1ms precision for anti-fingerprinting
2. **Garbage Collection**: Non-deterministic GC pauses affect timing measurements
3. **JIT Compilation**: Just-in-time compilation can introduce variable latency

### Constant-Time Properties

- Core ML-KEM operations use constant-time algorithms
- No secret-dependent branches in cryptographic core
- Barrett reduction is constant-time
- **Warning**: The JavaScript wrapper layer may not be constant-time due to engine optimizations

### Memory Security

- WASM heap memory is zeroized after use via `mlkem_zeroize()`
- JavaScript TypedArrays should be explicitly cleared
- Browser's memory model may retain data until GC

### Production Deployment Checklist

Before production use:

- [ ] Conduct TVLA evaluation (N ≥ 10,000)
- [ ] Test on target browser versions
- [ ] Review memory handling in your application layer
- [ ] Consider side-channel mitigations for your specific threat model
- [ ] Implement proper key lifecycle management

### Verified Test Vectors

Our implementation passes:
- NIST FIPS 203 test vectors
- Known-answer tests for all primitives
- Cross-validation against reference implementations

## Acknowledgments

We thank the cryptography community for responsible disclosure of any vulnerabilities.
