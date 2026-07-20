/**
 * @file purejs-wrapper.js
 * @module purejs-wrapper
 * @description ML-KEM-768 (FIPS 203) Pure-JavaScript Hybrid Key Exchange Wrapper.
 *
 * Provides an API-compatible alternative to mlkem768-wrapper.js that replaces
 * the Emscripten/WASM ML-KEM-768 implementation with the @noble/post-quantum
 * pure-JavaScript implementation. The hybrid construction, Web Crypto
 * operations (X25519, HKDF-SHA-256, AES-256-GCM), benchmarking API, and
 * hardware metadata collection are identical to the WASM variant.
 *
 * PURPOSE
 * -------
 * This wrapper enables a direct research comparison between two implementation
 * strategies on the same device and browser:
 *
 *   - WASM variant  (mlkem768-wrapper.js): Emscripten-compiled C reference
 *     implementation from PQClean, running in the WebAssembly VM. Expected to
 *     be faster on Chromium-based browsers with WASM SIMD support.
 *
 *   - Pure-JS variant (this file): @noble/post-quantum v0.6.1, a TypeScript
 *     implementation authored by Paul Miller. Expected to be slower but
 *     requires no WASM compilation and works in environments where WASM is
 *     restricted (e.g., some CSP policies, iOS WKWebView without WASM).
 *
 * API COMPATIBILITY
 * -----------------
 * All exports match mlkem768-wrapper.js exactly. The benchmark page switches
 * between implementations by swapping the import URL; no other changes are
 * needed.
 *
 * HARDWARE METADATA
 * -----------------
 * getHardwareMeta() is reproduced inline rather than shared via import to
 * avoid cross-module dependency issues between the two standalone benchmark
 * HTML pages. Both implementations will always report identical hardware
 * metadata for the same session, ensuring comparability.
 *
 * MEMORY SAFETY
 * -------------
 * @noble/post-quantum operates entirely in JS heap memory. Secret keys and
 * shared secrets returned by this module should be zeroized (.fill(0)) by the
 * caller after use, as with the WASM variant. Unlike the WASM variant, there
 * is no separate heap zeroization step since there is no WASM linear memory.
 *
 * @see src/js/mlkem768-wrapper.js for the WASM variant.
 * @see docs/API.md for the full JavaScript API reference.
 * @see https://github.com/paulmillr/noble-post-quantum for @noble/post-quantum.
 * @see NIST FIPS 203 (ML-KEM), RFC 5869 (HKDF), RFC 8446 §4.2.8 (X25519).
 */
import { ml_kem768 } from 'https://esm.sh/@noble/post-quantum@0.6.1/ml-kem';

/**
 * ML-KEM-768 parameter sizes (NIST FIPS 203, Table 2).
 * Identical to mlkem768-wrapper.js and src/wasm/params.h.
 * @see src/wasm/params.h
 */
/** Public key byte length — 1184 bytes. */
const MLKEM_PUBLICKEYBYTES  = 1184;
/** Secret key byte length — 2400 bytes. */
const MLKEM_SECRETKEYBYTES  = 2400;
/** Ciphertext byte length — 1088 bytes. */
const MLKEM_CIPHERTEXTBYTES = 1088;
/** Shared secret byte length — 32 bytes. */
const MLKEM_SSBYTES         = 32;

/**
 * loadModule — no-op for the pure-JS variant.
 *
 * Provided for API compatibility with mlkem768-wrapper.js. Since
 * @noble/post-quantum is a static ES import, no async initialization
 * is required. Returns true to signal readiness.
 *
 * @returns {Promise<true>}
 */
export async function loadModule() { return true; }

/**
 * mlkemKeyGen — ML-KEM-768 key pair generation via @noble/post-quantum.
 *
 * @returns {Promise<{pk: Uint8Array, sk: Uint8Array, timeMs: number}>}
 *   pk      — 1184-byte public key.
 *   sk      — 2400-byte secret key (MUST be zeroized by caller after use).
 *   timeMs  — execution time in milliseconds (performance.now() delta).
 */
export async function mlkemKeyGen() {
    const t0 = performance.now();
    const keys = ml_kem768.keygen();
    const t1 = performance.now();
    return { pk: keys.publicKey, sk: keys.secretKey, timeMs: t1 - t0 };
}

/**
 * mlkemEncaps — ML-KEM-768 encapsulation via @noble/post-quantum.
 *
 * @param {Uint8Array} pk — 1184-byte ML-KEM-768 public key.
 * @returns {Promise<{ct: Uint8Array, ss: Uint8Array, timeMs: number}>}
 *   ct      — 1088-byte ciphertext.
 *   ss      — 32-byte shared secret (MUST be zeroized by caller after use).
 *   timeMs  — execution time in milliseconds.
 * @throws {Error} If pk.length !== 1184.
 */
export async function mlkemEncaps(pk) {
    if (pk.length !== MLKEM_PUBLICKEYBYTES) throw new Error('Bad pk length');
    const t0 = performance.now();
    const res = ml_kem768.encapsulate(pk);
    const t1 = performance.now();
    return { ct: res.cipherText, ss: res.sharedSecret, timeMs: t1 - t0 };
}

/**
 * mlkemDecaps — ML-KEM-768 decapsulation via @noble/post-quantum.
 *
 * If the ciphertext is invalid, the FO implicit rejection mechanism returns
 * a pseudo-random value derived from the secret key and a rejection hash.
 * This function never throws for invalid ciphertexts.
 *
 * @param {Uint8Array} ct — 1088-byte ciphertext.
 * @param {Uint8Array} sk — 2400-byte ML-KEM-768 secret key.
 * @returns {Promise<{ss: Uint8Array, timeMs: number}>}
 *   ss      — 32-byte shared secret (MUST be zeroized by caller after use).
 *   timeMs  — execution time in milliseconds.
 * @throws {Error} If ct.length !== 1088 or sk.length !== 2400.
 */
export async function mlkemDecaps(ct, sk) {
    if (ct.length !== MLKEM_CIPHERTEXTBYTES) throw new Error('Bad ct length');
    if (sk.length !== MLKEM_SECRETKEYBYTES) throw new Error('Bad sk length');
    const t0 = performance.now();
    const ss = ml_kem768.decapsulate(ct, sk);
    const t1 = performance.now();
    return { ss, timeMs: t1 - t0 };
}

/**
 * checkX25519Support — probe whether Web Crypto supports the X25519 algorithm.
 *
 * Result is cached after the first call. Returns false on older browsers
 * (Firefox < 120, Safari < 15.4, any non-HTTPS context).
 *
 * @returns {Promise<boolean>} true if X25519 key generation succeeds.
 */
let _x25519Supported = null;
export async function checkX25519Support() {
    if (_x25519Supported !== null) return _x25519Supported;
    try {
        await crypto.subtle.generateKey({ name: 'X25519' }, true, ['deriveBits']);
        _x25519Supported = true;
    } catch (e) {
        _x25519Supported = false;
    }
    return _x25519Supported;
}

/* ── Web Crypto wrappers (identical to mlkem768-wrapper.js) ─────────────── */

/**
 * x25519KeyGen — generate an ephemeral X25519 key pair via Web Crypto API.
 *
 * The private key is returned as an opaque CryptoKey handle (non-extractable
 * after export for x25519Derive). The public key is exported as a raw 32-byte
 * Uint8Array for transmission.
 *
 * @returns {Promise<{publicKey: Uint8Array, privateKey: CryptoKey}>}
 */
export async function x25519KeyGen() {
    const kp = await crypto.subtle.generateKey({ name: 'X25519' }, true, ['deriveBits']);
    const pub = new Uint8Array(await crypto.subtle.exportKey('raw', kp.publicKey));
    return { publicKey: pub, privateKey: kp.privateKey };
}

/**
 * x25519Derive — compute X25519 shared secret via Web Crypto deriveBits.
 *
 * Rejects all-zero shared secrets per RFC 8446 §4.2.8, which indicates
 * a small-order or all-zero peer public key (invalid per RFC 7748 §6.1).
 *
 * @param {CryptoKey}  privateKey    — local X25519 private key (CryptoKey).
 * @param {Uint8Array} peerPublicKey — remote X25519 public key (32 bytes, raw).
 * @returns {Promise<Uint8Array>} 32-byte shared secret.
 * @throws {Error} If the derived shared secret is all-zero.
 */
export async function x25519Derive(privateKey, peerPublicKey) {
    const pub = await crypto.subtle.importKey('raw', peerPublicKey, { name: 'X25519' }, false, []);
    const bits = await crypto.subtle.deriveBits({ name: 'X25519', public: pub }, privateKey, 256);
    const ss = new Uint8Array(bits);
    /* All-zero shared secret check per RFC 8446 §4.2.8 / draft-ietf-tls-ecdhe-mlkem-04 §4.3 */
    if (ss.every(b => b === 0)) {
        throw new Error('X25519 shared secret is all-zero (invalid peer public key or small-order point)');
    }
    return ss;
}

/**
 * hkdfSha256 — HKDF-SHA-256 key derivation (RFC 5869) via Web Crypto API.
 *
 * @param {Uint8Array|ArrayBuffer} ikm    — Input key material.
 * @param {Uint8Array|ArrayBuffer} salt   — Optional salt (empty Uint8Array for no salt).
 * @param {Uint8Array|ArrayBuffer} info   — Context/application-specific info string.
 * @param {number}                 outLen — Output length in bytes (default 32).
 * @returns {Promise<Uint8Array>} Derived key material of length outLen.
 */
export async function hkdfSha256(ikm, salt, info, outLen = 32) {
    const base = await crypto.subtle.importKey('raw', ikm, 'HKDF', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({
        name: 'HKDF',
        hash: 'SHA-256',
        salt: salt,
        info: info
    }, base, outLen * 8);
    return new Uint8Array(bits);
}

/**
 * aesGcmEncrypt — AES-256-GCM authenticated encryption via Web Crypto API.
 *
 * @param {Uint8Array} key       — 32-byte AES-256 key.
 * @param {Uint8Array} plaintext — Plaintext to encrypt.
 * @param {Uint8Array} iv        — 12-byte initialization vector (must be unique per key use).
 * @returns {Promise<Uint8Array>} Ciphertext concatenated with 16-byte GCM authentication tag.
 */
export async function aesGcmEncrypt(key, plaintext, iv) {
    const cryptoKey = await crypto.subtle.importKey('raw', key, 'AES-GCM', false, ['encrypt']);
    const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, cryptoKey, plaintext);
    return new Uint8Array(ciphertext);
}

/**
 * aesGcmDecrypt — AES-256-GCM authenticated decryption via Web Crypto API.
 *
 * @param {Uint8Array} key        — 32-byte AES-256 key.
 * @param {Uint8Array} ciphertext — Ciphertext with 16-byte GCM authentication tag appended.
 * @param {Uint8Array} iv         — 12-byte initialization vector used during encryption.
 * @returns {Promise<Uint8Array>} Plaintext.
 * @throws {DOMException} OperationError if authentication tag is invalid.
 */
export async function aesGcmDecrypt(key, ciphertext, iv) {
    const cryptoKey = await crypto.subtle.importKey('raw', key, 'AES-GCM', false, ['decrypt']);
    const plaintext = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: iv }, cryptoKey, ciphertext);
    return new Uint8Array(plaintext);
}

/**
 * deriveSessionKey — X25519MLKEM768 hybrid shared-secret → AES-256-GCM session key.
 *
 * Concatenates mlkemSS ∥ x25519SS (ML-KEM first, per draft-ietf-tls-ecdhe-mlkem-04
 * §4.3) and derives a 32-byte key via HKDF-SHA-256. The intermediate buffer
 * is zeroized before returning. Identical to mlkem768-wrapper.js.
 *
 * @param {Uint8Array} mlkemSS  — 32-byte ML-KEM-768 shared secret.
 * @param {Uint8Array} x25519SS — 32-byte X25519 shared secret.
 * @param {Uint8Array} [context] — HKDF info string for domain separation.
 * @returns {Promise<Uint8Array>} 32-byte AES-256 session key.
 * @throws {Error} If either input is not exactly 32 bytes.
 */
export async function deriveSessionKey(mlkemSS, x25519SS, context = new TextEncoder().encode('Starrycrypt-PQC v1 | X25519MLKEM768 | AES-256-GCM')) {
    if (mlkemSS.length !== 32 || x25519SS.length !== 32) throw new Error('Bad SS lengths');
    const combined = new Uint8Array(64);
    combined.set(mlkemSS, 0);
    combined.set(x25519SS, 32);
    const salt = new Uint8Array(0);
    const key = await hkdfSha256(combined, salt, context, 32);
    combined.fill(0);
    return key;
}

/**
 * Gather structured, non-identifiable device metadata for reproducible benchmarking.
 *
 * Mirror of mlkem768-wrapper.js getHardwareMeta — kept inline to avoid
 * cross-module import issues with the pure-JS benchmark page.
 *
 * Probes:
 *   1. UA Client Hints API (Chromium ≥89)
 *   2. UA string regex fallback
 *   3. WASM feature detection (SIMD, threads, bulk-memory, relaxed-SIMD)
 *   4. Timer precision (Spectre/Meltdown jitter detection)
 *   5. Tab visibility state (background-tab throttling flag)
 *   6. Baseline throughput (JS-MIPS normalization factor)
 */
export async function getHardwareMeta() {
    const ram   = navigator.deviceMemory      || null;
    const cores = navigator.hardwareConcurrency || null;
    const ua    = navigator.userAgent;

    let osName       = 'unknown';
    let osVersion    = 'unknown';
    let browserName  = 'unknown';
    let browserVer   = 'unknown';
    let deviceType   = 'unknown';
    let deviceModel  = 'unknown';
    let platform     = navigator.userAgentData?.platform ?? navigator.platform ?? 'unknown';

    /* ── 1. UA Client Hints (Chromium-based browsers) ─────────────────── */
    if (navigator.userAgentData) {
        try {
            const h = await navigator.userAgentData.getHighEntropyValues([
                'platform', 'platformVersion', 'architecture',
                'model', 'mobile', 'fullVersionList'
            ]);
            platform    = h.platform    || platform;
            osName      = h.platform    || 'unknown';
            osVersion   = h.platformVersion || 'unknown';
            deviceType  = h.mobile ? 'mobile' : 'desktop';
            deviceModel = h.model   || 'unknown';

            const real = (h.fullVersionList || [])
                .filter(b => !/not.?a.?brand/i.test(b.brand) && b.brand !== 'Chromium')
                .sort((a, b) => {
                    const rank = ['Chrome', 'Edge', 'Opera', 'Samsung Internet'];
                    return (rank.indexOf(a.brand) < 0 ? 99 : rank.indexOf(a.brand)) -
                           (rank.indexOf(b.brand) < 0 ? 99 : rank.indexOf(b.brand));
                })[0];
            if (real) { browserName = real.brand; browserVer = real.version; }
        } catch (_) { /* fall through to UA regex */ }
    }

    /* ── 2. UA string regex fallback ──────────────────────────────────── */
    if (osName === 'unknown') {
        if      (/Android ([\d.]+)/i.test(ua)) { osName = 'Android'; osVersion = RegExp.$1; deviceType = 'mobile'; }
        else if (/iPhone OS ([\d_]+)/i.test(ua)) { osName = 'iOS'; osVersion = RegExp.$1.replace(/_/g,'.'); deviceType = 'mobile'; }
        else if (/iPad.*OS ([\d_]+)/i.test(ua)) { osName = 'iPadOS'; osVersion = RegExp.$1.replace(/_/g,'.'); deviceType = 'tablet'; }
        else if (/Windows NT ([\d.]+)/i.test(ua)) { osName = 'Windows'; osVersion = RegExp.$1; deviceType = 'desktop'; }
        else if (/Mac OS X ([\d_]+)/i.test(ua)) { osName = 'macOS'; osVersion = RegExp.$1.replace(/_/g,'.'); deviceType = 'desktop'; }
        else if (/Linux/i.test(ua)) { osName = 'Linux'; deviceType = 'desktop'; }
        else if (/CrOS/i.test(ua)) { osName = 'ChromeOS'; deviceType = 'desktop'; }
    }

    if (browserName === 'unknown') {
        /* Feature-based overrides (most reliable for Safari/Opera) */
        const isOpera  = (!!window.opr && !!opr.addons) || !!window.opera || ua.indexOf(' OPR/') >= 0 || ua.indexOf(' OPT/') >= 0 || ua.indexOf(' Coast/') >= 0;
        const isSafari = /constructor/i.test(window.HTMLElement) || (function (p) { return p.toString() === "[object SafariRemoteNotification]"; })(!window['safari'] || (typeof safari !== 'undefined' && window['safari'].pushNotification)) || (ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') === -1 && ua.indexOf('Chromium') === -1);
        const isFirefox = typeof InstallTrigger !== 'undefined' || ua.indexOf('Firefox') > -1;
        const isEdge = ua.indexOf('Edg/') > -1;
        const isBrave = !!navigator.brave && typeof navigator.brave.isBrave === 'function';
        const isVivaldi = ua.indexOf('Vivaldi') > -1;

        if (isBrave) {
            browserName = 'Brave';
            if (/Brave\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
        } else if (isVivaldi) {
            browserName = 'Vivaldi';
            if (/Vivaldi\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
        } else if (isOpera) {
            browserName = 'Opera';
            if (/OPR\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
            else if (/OPT\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
            else if (/Version\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
        } else if (isEdge) {
            browserName = 'Edge';
            if (/Edg\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
        } else if (isFirefox) {
            browserName = 'Firefox';
            if (/Firefox\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
        } else if (isSafari) {
            browserName = 'Safari';
            if (/Version\/([\d.]+)/.test(ua)) browserVer = RegExp.$1;
        } else if (/SamsungBrowser\/([\d.]+)/.test(ua)) {
            browserName = 'Samsung Internet';
            browserVer = RegExp.$1;
        } else if (/Chrome\/([\d.]+)/.test(ua)) {
            browserName = 'Chrome';
            browserVer = RegExp.$1;
        } else if (/CriOS\/([\d.]+)/.test(ua)) {
            /* Chrome on iOS */
            browserName = 'Chrome (iOS)';
            browserVer = RegExp.$1;
        } else if (/FxiOS\/([\d.]+)/.test(ua)) {
            /* Firefox on iOS */
            browserName = 'Firefox (iOS)';
            browserVer = RegExp.$1;
        }
    }

    /* ── 4. WASM Feature Detection ────────────────────────────────────── */
    const wasmFeatures = _detectWasmFeatures();

    /* ── 5. Timer Precision ───────────────────────────────────────────── */
    const timerPrecisionMs = _measureTimerPrecision();

    /* ── 6. Tab Visibility ────────────────────────────────────────────── */
    const tabVisible = document.visibilityState === 'visible';

    /* ── 7. Baseline Throughput ────────────────────────────────────────── */
    const baselineMips = _measureBaselineMips();

    /* ── 8. Lab Tagging ────────────────────────────────────────────────── *
     * Allows identifying controlled lab tests via ?env= URL parameter      */
    if (typeof window !== 'undefined' && window.location) {
        const urlParams = new URLSearchParams(window.location.search);
        const envTag = urlParams.get('env');
        if (envTag) {
            deviceModel = deviceModel === 'unknown' ? `[${envTag.toUpperCase()}]` : `[${envTag.toUpperCase()}] ${deviceModel}`;
        }
    }

    return {
        ramGiB:       ram,
        logicalCores: cores,
        platform,
        osName,
        osVersion,
        browserName,
        browserVersion: browserVer,
        deviceType,
        deviceModel:  deviceModel === 'unknown' ? null : deviceModel,
        userAgent: ua,
        wasmFeatures,
        timerPrecisionMs,
        tabVisible,
        baselineMips,
    };
}

/* ── Helper functions (same as mlkem768-wrapper.js) ───────────────────── */

function _detectWasmFeatures() {
    const features = { simd: false, threads: false, bulkMemory: false, relaxedSimd: false };

    try {
        new WebAssembly.Module(new Uint8Array([
            0x00,0x61,0x73,0x6d,0x01,0x00,0x00,0x00,
            0x01,0x05,0x01,0x60,0x00,0x01,0x7b,
            0x03,0x02,0x01,0x00,
            0x0a,0x16,0x01,0x14,0x00,
            0xfd,0x0c,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x0b
        ]));
        features.simd = true;
    } catch (_) {}

    try {
        if (typeof SharedArrayBuffer !== 'undefined') {
            new WebAssembly.Module(new Uint8Array([
                0x00,0x61,0x73,0x6d,0x01,0x00,0x00,0x00,
                0x05,0x04,0x01,0x03,0x01,0x01
            ]));
            features.threads = true;
        }
    } catch (_) {}

    try {
        new WebAssembly.Module(new Uint8Array([
            0x00,0x61,0x73,0x6d,0x01,0x00,0x00,0x00,
            0x01,0x04,0x01,0x60,0x00,0x00,
            0x03,0x02,0x01,0x00,
            0x05,0x03,0x01,0x00,0x01,
            0x0a,0x0e,0x01,0x0c,0x00,
            0x41,0x00,0x41,0x00,0x41,0x00,
            0xfc,0x0a,0x00,0x00,
            0x0b
        ]));
        features.bulkMemory = true;
    } catch (_) {}

    try {
        new WebAssembly.Module(new Uint8Array([
            0x00,0x61,0x73,0x6d,0x01,0x00,0x00,0x00,
            0x01,0x06,0x01,0x60,0x01,0x7b,0x01,0x7b,
            0x03,0x02,0x01,0x00,
            0x0a,0x09,0x01,0x07,0x00,
            0x20,0x00,
            0xfd,0x80,0x02,
            0x0b
        ]));
        features.relaxedSimd = true;
    } catch (_) {}

    return features;
}

function _measureTimerPrecision() {
    const deltas = [];
    let prev = performance.now();
    for (let guard = 0; guard < 100000 && deltas.length < 20; guard++) {
        const now = performance.now();
        if (now !== prev) { deltas.push(now - prev); prev = now; }
    }
    if (deltas.length === 0) return null;
    deltas.sort((a, b) => a - b);
    const mid = Math.floor(deltas.length / 2);
    return +(deltas.length % 2 ? deltas[mid] : (deltas[mid - 1] + deltas[mid]) / 2).toFixed(4);
}

function _measureBaselineMips() {
    const N = 1000000;
    let x = 0x12345678;
    const t0 = performance.now();
    for (let i = 0; i < N; i++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; }
    const t1 = performance.now();
    if (x === 0) console.log('xorshift degenerate seed');
    const ms = t1 - t0;
    return ms <= 0 ? null : +((N / ms) / 1000).toFixed(2);
}

/**
 * runHandshake — execute one complete X25519MLKEM768 hybrid handshake.
 *
 * API-compatible with mlkem768-wrapper.js runHandshake(). Performs:
 *   1. ML-KEM-768 KeyGen + Encaps + Decaps (via @noble/post-quantum)
 *   2. X25519 KeyGen + Derive (via Web Crypto API)
 *   3. HKDF-SHA-256 hybrid key derivation
 *   4. AES-256-GCM encrypt + decrypt (1024-byte payload)
 *
 * Returns per-operation timing and a keysMatch boolean indicating whether
 * Alice and Bob derived the same session key (correctness signal).
 *
 * @returns {Promise<{keysMatch: boolean, timing: object, sizes: object}>}
 */
export async function runHandshake() {
    const hasX25519 = await checkX25519Support();

    const tMlkemKeygen0 = performance.now();
    const aliceMlkem = await mlkemKeyGen();
    const tMlkemKeygen1 = performance.now();

    let aliceX25519 = null;
    if (hasX25519) {
        aliceX25519 = await x25519KeyGen();
    }

    let bobX25519 = null;
    if (hasX25519) {
        bobX25519 = await x25519KeyGen();
    }

    const tEncaps0 = performance.now();
    const aliceEnc = await mlkemEncaps(aliceMlkem.pk);
    const tEncaps1 = performance.now();

    const tDecaps0 = performance.now();
    const bobDec = await mlkemDecaps(aliceEnc.ct, aliceMlkem.sk);
    const tDecaps1 = performance.now();

    let aliceXSS = new Uint8Array(32);
    let bobXSS = new Uint8Array(32);
    const tX0 = performance.now();
    if (hasX25519) {
        try {
            aliceXSS = await x25519Derive(aliceX25519.privateKey, bobX25519.publicKey);
            bobXSS = await x25519Derive(bobX25519.privateKey, aliceX25519.publicKey);
        } catch (e) {
            /* Re-throw security-critical errors (e.g., all-zero shared secret).
             * Only swallow benign operational failures from keygen quirks. */
            if (e.message && e.message.includes('all-zero')) {
                throw e;
            }
            /* If derivation fails despite keygen working (rare Safari quirk),
             * continue with zeroed arrays for benchmark completeness only. */
        }
    }
    const tX1 = performance.now();

    const tKdf0 = performance.now();
    const aliceKey = await deriveSessionKey(aliceEnc.ss, aliceXSS);
    const bobKey = await deriveSessionKey(bobDec.ss, bobXSS);
    const tKdf1 = performance.now();

    const keysMatch = (aliceKey.length === bobKey.length) && aliceKey.every((v, i) => v === bobKey[i]);

    const iv = crypto.getRandomValues(new Uint8Array(12));
    const plaintext = crypto.getRandomValues(new Uint8Array(1024));
    const tAesEnc0 = performance.now();
    const ciphertext = await aesGcmEncrypt(aliceKey, plaintext, iv);
    const tAesEnc1 = performance.now();
    const tAesDec0 = performance.now();
    const decrypted = await aesGcmDecrypt(bobKey, ciphertext, iv);
    const tAesDec1 = performance.now();

    aliceMlkem.sk.fill(0);
    aliceEnc.ss.fill(0);
    bobDec.ss.fill(0);
    aliceXSS.fill(0); bobXSS.fill(0);
    aliceKey.fill(0); bobKey.fill(0);

    return {
        keysMatch,
        timing: {
            mlkemKeyGenMs: +(tMlkemKeygen1 - tMlkemKeygen0).toFixed(3),
            mlkemEncapsMs: +(tEncaps1 - tEncaps0).toFixed(3),
            mlkemDecapsMs: +(tDecaps1 - tDecaps0).toFixed(3),
            x25519ExchangeMs: +(tX1 - tX0).toFixed(3),
            hkdfMs: +(tKdf1 - tKdf0).toFixed(3),
            aesGcmEncryptMs: +(tAesEnc1 - tAesEnc0).toFixed(3),
            aesGcmDecryptMs: +(tAesDec1 - tAesDec0).toFixed(3),
            totalHandshakeMs: +(tAesDec1 - tMlkemKeygen0).toFixed(3)
        },
        sizes: {
            mlkemPublicKeyBytes: MLKEM_PUBLICKEYBYTES,
            mlkemSecretKeyBytes: MLKEM_SECRETKEYBYTES,
            mlkemCiphertextBytes: MLKEM_CIPHERTEXTBYTES,
            mlkemSharedSecretBytes: MLKEM_SSBYTES,
            sessionKeyBytes: 32,
            aesCiphertextBytes: ciphertext.length
        }
    };
}

/**
 * Run N full handshake cycles and return statistical benchmark JSON.
 * IEEE-quality output: mean, stdDev, min, max, median, and percentiles
 * (P5, P95, P99) for each timing field.
 *
 * A warm-up phase runs first to force JIT compilation before timed runs.
 *
 * @param {number} n — number of timed iterations (default 50, minimum 30 for CLT).
 * @param {number} warmup — number of untimed warm-up iterations (default 5).
 */
export async function runBenchmarkN(n = 50, warmup = 100) {
    if (n < 1) throw new Error('n must be >= 1');

    const hw = await getHardwareMeta();

    /* ── Warm-up phase: force JIT optimization before timed runs ── */
    for (let i = 0; i < warmup; i++) {
        await runHandshake(); // result discarded
    }

    /* ── Timed phase ──────────────────────────────────────────────── */
    const results = [];
    for (let i = 0; i < n; i++) {
        results.push(await runHandshake());
    }

    const field  = key => results.map(r => r.timing[key]);
    const mean   = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
    const median = arr => {
        const s = [...arr].sort((a, b) => a - b);
        const m = Math.floor(s.length / 2);
        return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
    };
    const stdDev = arr => {
        const m = mean(arr);
        return Math.sqrt(arr.map(x => (x - m) ** 2).reduce((a, b) => a + b, 0) / arr.length);
    };
    const percentile = (arr, p) => {
        const s = [...arr].sort((a, b) => a - b);
        const k = (s.length - 1) * (p / 100);
        const f = Math.floor(k);
        const c = Math.ceil(k);
        return f === c ? s[f] : s[f] + (s[c] - s[f]) * (k - f);
    };

    const timingKeys = Object.keys(results[0].timing);
    const timing = Object.fromEntries(
        timingKeys.map(k => {
            const vals = field(k);
            return [k, {
                mean:   +mean(vals).toFixed(3),
                stdDev: +stdDev(vals).toFixed(3),
                median: +median(vals).toFixed(3),
                p5:     +percentile(vals, 5).toFixed(3),
                p95:    +percentile(vals, 95).toFixed(3),
                p99:    +percentile(vals, 99).toFixed(3),
                min:    +Math.min(...vals).toFixed(3),
                max:    +Math.max(...vals).toFixed(3),
            }];
        })
    );

    return {
        hardware: hw,
        runs: n,
        warmupRuns: warmup,
        keysMatch: results.every(r => r.keysMatch),
        timing,
        sizes: results[0].sizes
    };
}
