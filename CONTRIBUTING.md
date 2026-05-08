# Contributing to StarryCrypt-PQC

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion:

1. Check if the issue already exists in the [issue tracker](https://github.com/Samin-yasar/starrycrypt-pqc/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Browser/environment details
   - Screenshots if applicable

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests and verification (`make test`)
5. Commit with clear messages
6. Push to your fork
7. Open a pull request

### Code Style

#### C Code (WASM)
- Follow Linux kernel style for C code
- Use 4-space indentation
- Keep lines under 80 characters
- Comment complex cryptographic operations

#### JavaScript
- Use ES6+ features
- 2-space indentation
- JSDoc comments for public APIs
- Async/await preferred over promises

#### Python (Analysis)
- Follow PEP 8
- Use type hints where appropriate
- Document functions with docstrings

### Testing

Before submitting:

```bash
# Build WASM
make all

# Run verification
make verify-stats

# Generate figures (if modifying analysis)
make figures
```

### Areas for Contribution

- **Performance**: SIMD optimizations, JavaScript engine tuning
- **Testing**: Additional test vectors, edge case handling
- **Documentation**: README improvements, API docs, tutorials
- **Analysis**: Additional statistical methods, visualization improvements
- **Compatibility**: Additional browser testing, mobile optimization

### Security

If you discover a security vulnerability:
1. **DO NOT** open a public issue
2. Email research@samin-yasar.dev with details
3. Allow time for assessment before public disclosure

### Questions?

- Open a [GitHub Discussion](https://github.com/Samin-yasar/starrycrypt-pqc/discussions)
- Email: research@samin-yasar.dev

## License

By contributing, you agree that your contributions will be licensed under the [LICENSE](https://github.com/Samin-yasar/Starrycrypt-PQC-Research/blob/main/LICENSE).
