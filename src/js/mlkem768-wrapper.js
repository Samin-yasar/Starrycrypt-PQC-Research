/**
 * ML-KEM-768 (FIPS 203) Hybrid Wrapper
 * Combines ML-KEM shared secret with X25519 using HKDF-SHA-256 (Web Crypto API)
 */

const MLKEM_PUBLICKEYBYTES = 1184;
const MLKEM_SECRETKEYBYTES = 2400;
const MLKEM_CIPHERTEXTBYTES = 1088;
const MLKEM_SSBYTES = 32;

let Module = null;
let moduleLoadPromise = null;

/** Load the WASM module. Call once before any operations. */
export async function loadModule(wasmUrl = './dist/mlkem768.js') {
    if (Module) return Module;
    // Cache the in-flight promise so concurrent callers all await the same
    // load/init path and only one <script> tag is ever injected.
    if (!moduleLoadPromise) {
        moduleLoadPromise = _doLoadModule(wasmUrl);
    }
    try {
        Module = await moduleLoadPromise;
    } catch (err) {
        moduleLoadPromise = null; // allow retry on failure
        throw err;
    }
    return Module;
}

async function _doLoadModule(wasmUrl) {
    // mlkem768.js is an Emscripten classic (non-module) build.  Loading it via
    // dynamic import() would return an empty module with no .default export,
    // and would also break WASM path resolution because document.currentScript
    // is null inside ES modules.  Instead inject a plain <script> tag so the
    // file runs in global scope, sets window.MLKEMModule, and lets Emscripten
    // read document.currentScript.src to derive the correct .wasm path.
    if (typeof window.MLKEMModule !== 'function') {
        const container = document.head || document.body || document.documentElement;
        if (!container) throw new Error('Cannot inject WASM script: no DOM container found');
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = wasmUrl;
            script.onload = resolve;
            script.onerror = () => reject(new Error('Failed to load WASM script: ' + wasmUrl));
            container.appendChild(script);
        });
    }
    if (typeof window.MLKEMModule !== 'function') {
        throw new Error(
            `WASM factory (window.MLKEMModule) was not defined after loading "${wasmUrl}". ` +
            'Verify the URL points to the correct Emscripten build.'
        );
    }
    let mod = window.MLKEMModule();
    // Emscripten may return either the Module directly or a Promise
    if (mod && typeof mod.then === 'function') {
        mod = await mod;
    }
    // If there's a ready promise, wait for it
    if (mod && mod.ready && typeof mod.ready.then === 'function') {
        await mod.ready;
    }
    if (!mod || !mod.HEAPU8) {
        throw new Error(
            `WASM module loaded but heap not initialized. ` +
            'This usually means the .wasm binary failed to load (check network tab for 404).'
        );
    }
    return mod;
}

function _malloc(n) {
    if (!Module) throw new Error('WASM module not initialized');
    return Module.ccall('mlkem_malloc', 'number', ['number'], [n]);
}
function _free(ptr) {
    if (!Module) throw new Error('WASM module not initialized');
    Module.ccall('mlkem_free', null, ['number'], [ptr]);
}
function _zeroize(ptr, n) {
    if (!Module) throw new Error('WASM module not initialized');
    Module.ccall('mlkem_zeroize', null, ['number', 'number'], [ptr, n]);
}
function heapWrite(src, ptr, len) {
    if (!Module) throw new Error('WASM module not initialized');
    if (src.length !== len) throw new Error(`heapWrite: src.length (${src.length}) !== expected len (${len})`);
    Module.writeArrayToMemory(src, ptr);
}
function heapRead(ptr, len) {
    if (!Module || !Module.HEAPU8) throw new Error('WASM heap not initialized');
    return new Uint8Array(Module.HEAPU8.buffer, ptr, len).slice();
}

/** Generate ML-KEM-768 keypair. Returns {pk, sk, timeMs}. */
export async function mlkemKeyGen() {
    const pkPtr = _malloc(MLKEM_PUBLICKEYBYTES);
    const skPtr = _malloc(MLKEM_SECRETKEYBYTES);
    try {
        const t0 = performance.now();
        const ret = Module.ccall('mlkem_keypair', 'number', ['number', 'number'], [pkPtr, skPtr]);
        const t1 = performance.now();
        if (ret !== 0) throw new Error('mlkem_keypair failed: ' + ret);
        const pk = heapRead(pkPtr, MLKEM_PUBLICKEYBYTES);
        const sk = heapRead(skPtr, MLKEM_SECRETKEYBYTES);
        return { pk, sk, timeMs: t1 - t0 };
    } finally {
        _zeroize(skPtr, MLKEM_SECRETKEYBYTES); /* sk is secret — wipe before free */
        _free(skPtr);
        _free(pkPtr); /* pk is public — zeroization not required */
    }
}

/** Encapsulate to a public key. Returns {ct, ss, timeMs}. */
export async function mlkemEncaps(pk) {
    if (pk.length !== MLKEM_PUBLICKEYBYTES) throw new Error('Bad pk length');
    const ctPtr = _malloc(MLKEM_CIPHERTEXTBYTES);
    const ssPtr = _malloc(MLKEM_SSBYTES);
    const pkPtr = _malloc(MLKEM_PUBLICKEYBYTES);
    try {
        heapWrite(pk, pkPtr, MLKEM_PUBLICKEYBYTES);
        const t0 = performance.now();
        const ret = Module.ccall('mlkem_enc', 'number', ['number', 'number', 'number'], [ctPtr, ssPtr, pkPtr]);
        const t1 = performance.now();
        if (ret !== 0) throw new Error('mlkem_enc failed: ' + ret);
        const ct = heapRead(ctPtr, MLKEM_CIPHERTEXTBYTES);
        const ss = heapRead(ssPtr, MLKEM_SSBYTES);
        return { ct, ss, timeMs: t1 - t0 };
    } finally {
        _zeroize(ssPtr, MLKEM_SSBYTES);
        _zeroize(pkPtr, MLKEM_PUBLICKEYBYTES);
        _free(ctPtr);
        _free(ssPtr);
        _free(pkPtr);
    }
}

/** Decapsulate with a secret key. Returns {ss, timeMs}. */
export async function mlkemDecaps(ct, sk) {
    if (ct.length !== MLKEM_CIPHERTEXTBYTES) throw new Error('Bad ct length');
    if (sk.length !== MLKEM_SECRETKEYBYTES) throw new Error('Bad sk length');
    const ssPtr = _malloc(MLKEM_SSBYTES);
    const ctPtr = _malloc(MLKEM_CIPHERTEXTBYTES);
    const skPtr = _malloc(MLKEM_SECRETKEYBYTES);
    try {
        heapWrite(ct, ctPtr, MLKEM_CIPHERTEXTBYTES);
        heapWrite(sk, skPtr, MLKEM_SECRETKEYBYTES);
        const t0 = performance.now();
        const ret = Module.ccall('mlkem_dec', 'number', ['number', 'number', 'number'], [ssPtr, ctPtr, skPtr]);
        const t1 = performance.now();
        if (ret !== 0) throw new Error('mlkem_dec failed: ' + ret);
        const ss = heapRead(ssPtr, MLKEM_SSBYTES);
        return { ss, timeMs: t1 - t0 };
    } finally {
        _zeroize(ssPtr, MLKEM_SSBYTES);
        _zeroize(skPtr, MLKEM_SECRETKEYBYTES);
        _free(ssPtr);
        _free(ctPtr);
        _free(skPtr);
    }
}

/** Check if X25519 is supported by the browser's WebCrypto implementation. */
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

/**
 * X25519 Key Generation via Web Crypto API.
 * Returns the CryptoKey handle directly — private scalar is never exported to JS heap.
 */
export async function x25519KeyGen() {
    const kp = await crypto.subtle.generateKey({ name: 'X25519' }, true, ['deriveBits']);
    const pub = new Uint8Array(await crypto.subtle.exportKey('raw', kp.publicKey));
    return { publicKey: pub, privateKey: kp.privateKey };
}

/**
 * X25519 shared secret derivation via Web Crypto API.
 * @param {CryptoKey} privateKey — the CryptoKey returned by x25519KeyGen.
 * @param {Uint8Array} peerPublicKey — the peer's 32-byte raw public key.
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

/** HKDF-SHA-256 via Web Crypto API. */
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

/** AES-256-GCM encrypt via Web Crypto API. */
export async function aesGcmEncrypt(key, plaintext, iv) {
    const cryptoKey = await crypto.subtle.importKey('raw', key, 'AES-GCM', false, ['encrypt']);
    const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, cryptoKey, plaintext);
    return new Uint8Array(ciphertext);
}

/** AES-256-GCM decrypt via Web Crypto API. */
export async function aesGcmDecrypt(key, ciphertext, iv) {
    const cryptoKey = await crypto.subtle.importKey('raw', key, 'AES-GCM', false, ['decrypt']);
    const plaintext = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: iv }, cryptoKey, ciphertext);
    return new Uint8Array(plaintext);
}

/**
 * Hybrid key derivation: ML-KEM ss || X25519 ss -> HKDF-SHA-256 -> AES-256-GCM key.
 * Concatenation order follows draft-ietf-tls-ecdhe-mlkem-04 §4.3 (ML-KEM first).
 * Info string provides application-level domain separation per RFC 5869 §3.2.
 */
export async function deriveSessionKey(mlkemSS, x25519SS, context = new TextEncoder().encode('Starrycrypt-PQC v1 | X25519MLKEM768 | AES-256-GCM')) {
    if (mlkemSS.length !== 32 || x25519SS.length !== 32) throw new Error('Bad SS lengths');
    const combined = new Uint8Array(64);
    combined.set(mlkemSS, 0);
    combined.set(x25519SS, 32);
    const salt = new Uint8Array(0); /* empty salt per HKDF spec */
    const key = await hkdfSha256(combined, salt, context, 32);
    /* zeroize intermediate */
    combined.fill(0);
    return key;
}

/**
 * Gather structured, non-identifiable device metadata for reproducible benchmarking.
 *
 * Priority order:
 *   1. UA Client Hints API (Chrome/Edge ≥89) — most accurate on Android/Windows.
 *   2. UA string regex fallback              — covers Firefox, Safari, older browsers.
 *
 * Additional probes (IEEE-quality research metadata):
 *   3. WASM feature detection — SIMD, threads, bulk-memory, relaxed-SIMD.
 *   4. Timer precision        — measures actual performance.now() tick granularity.
 *   5. Tab visibility state   — flags background-tab throttling as data quality signal.
 *   6. Baseline throughput    — JS-MIPS normalization factor for cross-device comparison.
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

            /* Filter out "Not A;Brand" noise and pick the real browser */
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

    /* ── 4. WASM Feature Detection ────────────────────────────────────── *
     * Detect hardware-accelerated WASM features that directly impact
     * ML-KEM throughput.  SIMD enables 128-bit vector NTT operations;
     * threads enable shared-memory parallelism via SharedArrayBuffer.
     * Results explain performance "clusters" across devices.              */
    const wasmFeatures = _detectWasmFeatures();

    /* ── 5. Timer Precision (Spectre/Meltdown jitter detection) ───────── *
     * Browsers may coarsen performance.now() to 100µs or 1ms to mitigate
     * timing side-channels.  If precision is worse than 5µs, sub-ms
     * operations (like ML-KEM Encaps on fast hardware) may show
     * quantization noise that inflates stdDev.                            */
    const timerPrecisionMs = _measureTimerPrecision();

    /* ── 6. Tab Visibility & Throttling State ─────────────────────────── *
     * Background tabs get their timers throttled to 1Hz (or worse on
     * mobile).  Benchmarks run while hidden produce invalid timing data.
     * We record the state at capture time so the analysis pipeline can
     * filter or flag these results.                                       */
    const tabVisible = document.visibilityState === 'visible';

    /* ── 7. Baseline Throughput — JS-MIPS Normalization Factor ────────── *
     * A short, deterministic integer-math loop gives a device-specific
     * "speed score" independent of crypto implementation.  This allows
     * the analysis pipeline to normalize timing data across wildly
     * different hardware (e.g., $200 Android vs $2000 MacBook).           */
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
        userAgent: ua,  /* retained for audit/debug; NOT used as an identifier */
        wasmFeatures,
        timerPrecisionMs,
        tabVisible,
        baselineMips,
    };
}

/**
 * Detect WASM feature support by attempting to compile minimal feature-gated
 * modules.  Each probe is a hand-crafted binary that uses exactly one
 * proposal-specific instruction, so compilation will fail cleanly on engines
 * that don't support it.
 *
 * References:
 *   - SIMD: github.com/AJMcCarthy/AJMcCarthy/wasm-feature-detect (v128.const)
 *   - Threads: requires SharedArrayBuffer + Atomics
 *   - Bulk Memory: memory.copy instruction
 *   - Relaxed SIMD: i32x4.relaxed_trunc_f32x4_s
 */
function _detectWasmFeatures() {
    const features = {
        simd: false,
        threads: false,
        bulkMemory: false,
        relaxedSimd: false,
    };

    /* SIMD — v128.const (opcode 0xFD 0x0C) */
    try {
        new WebAssembly.Module(new Uint8Array([
            0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, // magic + version
            0x01, 0x05, 0x01, 0x60, 0x00, 0x01, 0x7b,       // type section: () -> v128
            0x03, 0x02, 0x01, 0x00,                         // function section
            0x0a, 0x16, 0x01, 0x14, 0x00,                   // code section
            0xfd, 0x0c,                                     // v128.const
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x0b                                            // end
        ]));
        features.simd = true;
    } catch (_) {}

    /* Threads — requires SharedArrayBuffer */
    try {
        if (typeof SharedArrayBuffer !== 'undefined') {
            new WebAssembly.Module(new Uint8Array([
                0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
                0x05, 0x04, 0x01, 0x03, 0x01, 0x01             // shared memory: 1 page, max 1
            ]));
            features.threads = true;
        }
    } catch (_) {}

    /* Bulk Memory — memory.copy (opcode 0xFC 0x0A) */
    try {
        new WebAssembly.Module(new Uint8Array([
            0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
            0x01, 0x04, 0x01, 0x60, 0x00, 0x00,             // type: () -> void
            0x03, 0x02, 0x01, 0x00,                         // func
            0x05, 0x03, 0x01, 0x00, 0x01,                   // memory: 1 page
            0x0a, 0x0e, 0x01, 0x0c, 0x00,                   // code section
            0x41, 0x00, 0x41, 0x00, 0x41, 0x00,             // i32.const 0, 0, 0
            0xfc, 0x0a, 0x00, 0x00,                         // memory.copy 0 0
            0x0b                                            // end
        ]));
        features.bulkMemory = true;
    } catch (_) {}

    /* Relaxed SIMD — i32x4.relaxed_trunc_f32x4_s (opcode 0xFD 0x80 0x02) */
    try {
        new WebAssembly.Module(new Uint8Array([
            0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
            0x01, 0x06, 0x01, 0x60, 0x01, 0x7b, 0x01, 0x7b, // type: (v128) -> v128
            0x03, 0x02, 0x01, 0x00,                         // func
            0x0a, 0x09, 0x01, 0x07, 0x00,                   // code section
            0x20, 0x00,                                     // local.get 0
            0xfd, 0x80, 0x02,                               // i32x4.relaxed_trunc_f32x4_s
            0x0b                                            // end
        ]));
        features.relaxedSimd = true;
    } catch (_) {}

    return features;
}

/**
 * Measure the effective tick granularity of performance.now().
 *
 * Runs a tight loop collecting timestamps until it observes 20 distinct
 * transitions, then returns the median delta.  On un-jittered Chrome this
 * will report ~0.005 ms (5 µs); on Firefox with resistFingerprinting it
 * will typically report 0.1 ms or 1.0 ms.
 */
function _measureTimerPrecision() {
    const TARGET_TRANSITIONS = 20;
    const deltas = [];
    let prev = performance.now();

    for (let guard = 0; guard < 100000 && deltas.length < TARGET_TRANSITIONS; guard++) {
        const now = performance.now();
        if (now !== prev) {
            deltas.push(now - prev);
            prev = now;
        }
    }

    if (deltas.length === 0) return null;

    /* Return median delta to filter outliers from OS scheduling jitter */
    deltas.sort((a, b) => a - b);
    const mid = Math.floor(deltas.length / 2);
    const precision = deltas.length % 2
        ? deltas[mid]
        : (deltas[mid - 1] + deltas[mid]) / 2;

    return +precision.toFixed(4);
}

/**
 * Compute a device-specific "JS-MIPS" score: the number of millions of
 * simple integer operations per second achievable in a tight JS loop.
 *
 * The workload is a deterministic 32-bit xorshift PRNG — it is pure ALU
 * work with no memory pressure, GC triggers, or async boundaries, making
 * it a stable baseline across browsers.  The loop runs for ~20 ms to stay
 * below perceptible UI jank.
 *
 * Usage in analysis: normalizedTime = rawMs * (referenceMips / deviceMips).
 */
function _measureBaselineMips() {
    const ITERATIONS = 1000000;
    let x = 0x12345678; /* deterministic seed */

    const t0 = performance.now();
    for (let i = 0; i < ITERATIONS; i++) {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
    }
    const t1 = performance.now();

    /* Prevent dead-code elimination — force the engine to keep x alive */
    if (x === 0) console.log('xorshift degenerate seed');

    const elapsedMs = t1 - t0;
    if (elapsedMs <= 0) return null;

    /* Millions of operations per second */
    return +((ITERATIONS / elapsedMs) / 1000).toFixed(2);
}

/**
 * Run one full handshake cycle and return benchmark JSON.
 */
export async function runHandshake() {
    const hasX25519 = await checkX25519Support();

    /* --- Alice (initiator) --- */
    const tMlkemKeygen0 = performance.now();
    const aliceMlkem = await mlkemKeyGen();
    const tMlkemKeygen1 = performance.now();
    
    let aliceX25519 = null;
    if (hasX25519) {
        aliceX25519 = await x25519KeyGen();
    }

    /* --- Bob (responder) --- */
    let bobX25519 = null;
    if (hasX25519) {
        bobX25519 = await x25519KeyGen();
    }

    /* Encapsulation */
    const tEncaps0 = performance.now();
    const aliceEnc = await mlkemEncaps(aliceMlkem.pk);
    const tEncaps1 = performance.now();

    /* Decapsulation */
    const tDecaps0 = performance.now();
    const bobDec = await mlkemDecaps(aliceEnc.ct, aliceMlkem.sk);
    const tDecaps1 = performance.now();

    /* X25519 key exchange */
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

    /* Hybrid key derivation */
    const tKdf0 = performance.now();
    const aliceKey = await deriveSessionKey(aliceEnc.ss, aliceXSS);
    const bobKey = await deriveSessionKey(bobDec.ss, bobXSS);
    const tKdf1 = performance.now();

    /* Verify key agreement */
    const keysMatch = (aliceKey.length === bobKey.length) && aliceKey.every((v, i) => v === bobKey[i]);

    /* AES-GCM round-trip benchmark */
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const plaintext = crypto.getRandomValues(new Uint8Array(1024));
    const tAesEnc0 = performance.now();
    const ciphertext = await aesGcmEncrypt(aliceKey, plaintext, iv);
    const tAesEnc1 = performance.now();
    const tAesDec0 = performance.now();
    const decrypted = await aesGcmDecrypt(bobKey, ciphertext, iv);
    const tAesDec1 = performance.now();

    /* Zeroize JS-accessible secrets.
     * X25519 private keys are CryptoKey handles — their memory is managed by
     * the browser's Web Crypto implementation and is not accessible from JS. */
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
 * A warm-up phase of WARMUP_ROUNDS dummy iterations runs first to force
 * JIT compilation of the WASM module before the timed window begins.
 * This prevents first-run compilation overhead from skewing results.
 *
 * @param {number} n — number of timed iterations (default 50, minimum 30 for CLT).
 * @param {number} warmup — number of untimed warm-up iterations (default 5).
 */
export async function runBenchmarkN(n = 50, warmup = 100) {
    if (n < 1) throw new Error('n must be >= 1');

    const hw = await getHardwareMeta();

    /* ── Warm-up phase: force JIT/WASM optimization before timed runs ── */
    for (let i = 0; i < warmup; i++) {
        await runHandshake(); // result discarded
    }

    /* ── Timed phase ──────────────────────────────────────────────────── */
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

/**
 * Runtime self-test: performs a full keygen → encaps → decaps round-trip
 * and verifies shared-secret agreement. Returns a structured report.
 *
 * This serves as a KAT-like sanity check that the FIPS 203 implementation
 * is producing correct output, not just correct-length output. Call before
 * benchmarking to give reviewers confidence in cryptographic correctness.
 */
export async function selfTest() {
    const kp = await mlkemKeyGen();

    /* Verify byte lengths match FIPS 203 ML-KEM-768 exactly */
    const checks = [
        { name: 'pk length',  actual: kp.pk.length,  expected: MLKEM_PUBLICKEYBYTES },
        { name: 'sk length',  actual: kp.sk.length,  expected: MLKEM_SECRETKEYBYTES },
    ];

    const enc = await mlkemEncaps(kp.pk);
    checks.push(
        { name: 'ct length',  actual: enc.ct.length,  expected: MLKEM_CIPHERTEXTBYTES },
        { name: 'ss length',  actual: enc.ss.length,  expected: MLKEM_SSBYTES },
    );

    const dec = await mlkemDecaps(enc.ct, kp.sk);
    checks.push(
        { name: 'dec ss length', actual: dec.ss.length, expected: MLKEM_SSBYTES },
    );

    /* Shared-secret agreement */
    const ssMatch = enc.ss.length === dec.ss.length &&
                    enc.ss.every((v, i) => v === dec.ss[i]);
    checks.push({ name: 'shared secret agreement', actual: ssMatch, expected: true });

    /* Hybrid round-trip */
    const aliceX = await x25519KeyGen();
    const bobX   = await x25519KeyGen();
    const aliceXSS = await x25519Derive(aliceX.privateKey, bobX.publicKey);
    const bobXSS   = await x25519Derive(bobX.privateKey,   aliceX.publicKey);
    const aliceKey  = await deriveSessionKey(enc.ss,  aliceXSS);
    const bobKey    = await deriveSessionKey(dec.ss, bobXSS);
    const hybridMatch = aliceKey.every((v, i) => v === bobKey[i]);
    checks.push({ name: 'hybrid key agreement', actual: hybridMatch, expected: true });

    /* Zeroize */
    kp.sk.fill(0); enc.ss.fill(0); dec.ss.fill(0);
    aliceXSS.fill(0); bobXSS.fill(0); aliceKey.fill(0); bobKey.fill(0);

    const allPassed = checks.every(c => c.actual === c.expected);
    return { passed: allPassed, checks };
}

/**
 * Verify constant-time behavior of the Fujisaki-Okamoto rejection path.
 *
 * Corrupts one byte of a valid ciphertext, then compares decapsulation
 * timing of the valid vs. corrupted ciphertext over N trials.  If the
 * implementation is constant-time, the mean timings should be statistically
 * indistinguishable (small |Δ| relative to σ).
 *
 * Returns the timing statistics for both paths and the t-statistic.
 * A |t| < 2.0 (at N≥30) indicates no statistically significant timing
 * difference at the 95% confidence level.
 *
 * @param {number} n — iterations per path (default 100).
 */
export async function verifyConstantTimeRejection(n = 100) {
    const kp  = await mlkemKeyGen();
    const enc = await mlkemEncaps(kp.pk);

    /* Create a corrupted ciphertext (flip one bit in byte 0) */
    const ctBad = new Uint8Array(enc.ct);
    ctBad[0] ^= 0x01;

    const warmup = 5;

    /* Warm-up */
    for (let i = 0; i < warmup; i++) {
        await mlkemDecaps(enc.ct, kp.sk);
        await mlkemDecaps(ctBad,  kp.sk);
    }

    /* Timed runs — interleave valid/invalid to avoid ordering bias */
    const validTimes   = [];
    const invalidTimes = [];
    for (let i = 0; i < n; i++) {
        const dv = await mlkemDecaps(enc.ct, kp.sk);
        validTimes.push(dv.timeMs);

        const di = await mlkemDecaps(ctBad,  kp.sk);
        invalidTimes.push(di.timeMs);
    }

    const mean   = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
    const stdDev = arr => {
        const m = mean(arr);
        return Math.sqrt(arr.map(x => (x - m) ** 2).reduce((a, b) => a + b, 0) / arr.length);
    };

    const mV = mean(validTimes),   sV = stdDev(validTimes);
    const mI = mean(invalidTimes), sI = stdDev(invalidTimes);

    /* Welch's t-test (unequal variance) */
    const se = Math.sqrt((sV ** 2) / n + (sI ** 2) / n);
    const t  = se > 0 ? (mV - mI) / se : 0;

    /* Zeroize */
    kp.sk.fill(0); enc.ss.fill(0);

    return {
        validPath:   { mean: +mV.toFixed(4), stdDev: +sV.toFixed(4), n },
        invalidPath: { mean: +mI.toFixed(4), stdDev: +sI.toFixed(4), n },
        tStatistic:  +t.toFixed(4),
        constantTime: Math.abs(t) < 2.0,
        interpretation: Math.abs(t) < 2.0
            ? 'No statistically significant timing difference (p > 0.05). FO rejection path appears constant-time.'
            : 'WARNING: Timing difference detected (|t| >= 2.0). Investigate potential side-channel leakage.'
    };
}
