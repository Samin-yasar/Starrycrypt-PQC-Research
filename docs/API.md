# API Documentation

## WASM Implementation

### Module Loading

```javascript
import { loadModule } from './src/js/mlkem768-wrapper.js';

// Load with default path
await loadModule();

// Or specify custom path
await loadModule('./custom/path/mlkem768.js');
```

### Key Generation

```javascript
import { generateKeypair } from './src/js/mlkem768-wrapper.js';

const { publicKey, secretKey } = await generateKeypair();

// publicKey: Uint8Array (1184 bytes)
// secretKey: Uint8Array (2400 bytes)
```

### Encapsulation (Client)

```javascript
import { encapsulate } from './src/js/mlkem768-wrapper.js';

const { ciphertext, sharedSecret } = await encapsulate(publicKey);

// ciphertext: Uint8Array (1088 bytes)
// sharedSecret: Uint8Array (32 bytes)
```

### Decapsulation (Server)

```javascript
import { decapsulate } from './src/js/mlkem768-wrapper.js';

const sharedSecret = await decapsulate(ciphertext, secretKey);

// sharedSecret: Uint8Array (32 bytes)
```

### Hybrid Key Exchange (ML-KEM + X25519)

```javascript
import { generateHybridKeypair, hybridEncapsulate, hybridDecapsulate } from './src/js/mlkem768-wrapper.js';

// Generate hybrid keypair
const { mlkemPublicKey, x25519PublicKey, mlkemSecretKey, x25519SecretKey } = 
    await generateHybridKeypair();

// Encapsulate
const { ciphertext, kemCiphertext, sharedSecret } = 
    await hybridEncapsulate(mlkemPublicKey, x25519PublicKey);

// Decapsulate  
const sharedSecret = await hybridDecapsulate(
    ciphertext, 
    kemCiphertext,
    mlkemSecretKey, 
    x25519SecretKey
);
```

### Memory Management

```javascript
import { zeroize } from './src/js/mlkem768-wrapper.js';

// Securely clear sensitive material
zeroize(secretKey);
zeroize(sharedSecret);
```

## Pure JavaScript Implementation

Same API as WASM version, just import from different module:

```javascript
import { generateKeypair, encapsulate, decapsulate } from './src/js/purejs-wrapper.js';

// Usage is identical to WASM version
const { publicKey, secretKey } = await generateKeypair();
```

## Benchmarking API

```javascript
import { runBenchmark } from './src/js/telemetry.js';

const results = await runBenchmark({
    iterations: 100,
    warmup: 10,
    enableTelemetry: true
});

// Returns: { keygen, encaps, decaps, total, metadata }
```

## Constant-Time Testing

```javascript
import { runCTTest } from './src/js/telemetry.js';

const result = await runCTTest({
    iterations: 100,  // Low sample size for quick screening
    mode: 'fo-rejection'  // Test FO transform rejection path
});

// Returns: { tStat, meanValid, meanInvalid, passed }
// Note: |tStat| < 2.0 suggests no gross leakage at this sample size
```

## Error Handling

All functions throw descriptive errors:

```javascript
try {
    const { sharedSecret } = await encapsulate(invalidKey);
} catch (err) {
    console.error('Encapsulation failed:', err.message);
}
```

## Constants

```javascript
const CONSTANTS = {
    MLKEM_PUBLICKEYBYTES: 1184,
    MLKEM_SECRETKEYBYTES: 2400,
    MLKEM_CIPHERTEXTBYTES: 1088,
    MLKEM_SSBYTES: 32
};
```
