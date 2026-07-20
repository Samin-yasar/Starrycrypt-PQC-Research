/**
 * @file randombytes.c
 * @brief Platform-dispatched cryptographic random byte generation.
 *
 * Provides a single public function:
 *
 *   int randombytes(uint8_t *output, size_t n);
 *
 * which fills n bytes of output from the operating system or runtime's
 * cryptographically secure pseudorandom number generator (CSPRNG).
 *
 * PLATFORM DISPATCH TABLE
 * -----------------------
 * The correct implementation is selected at compile time via preprocessor
 * macros. The dispatch order is:
 *
 *   __EMSCRIPTEN__  → Web Crypto API (globalThis.crypto.getRandomValues)
 *   __linux__       → getrandom(2) syscall (glibc >= 2.25 or SYS_getrandom)
 *                     Falls back to /dev/urandom with entropy-wait on older kernels.
 *   BSD             → arc4random_buf(3)
 *   _WIN32          → CryptGenRandom (CryptoAPI)
 *   __wasi__        → arc4random_buf (WASI stdlib)
 *
 * EMSCRIPTEN (WASM) PATH
 * ----------------------
 * In the WASM build (the primary target for this research codebase), entropy
 * is drawn from the Web Crypto API via EM_ASM_INT. The implementation tries:
 *   1. globalThis.crypto  (main thread, Web Workers, Service Workers)
 *   2. self.crypto        (Web Worker fallback)
 *   3. window.crypto      (legacy browser fallback)
 *
 * If none of these are available (e.g., non-secure context or very old
 * browser), the function returns -1 and sets errno = EINVAL. Callers
 * (kem.c, keypair, encaps) check the return value and propagate errors.
 *
 * LINUX PATH
 * ----------
 * Uses getrandom(2) when available (glibc >= 2.25 or SYS_getrandom), which
 * blocks until the kernel's entropy pool is initialized and then never blocks
 * again. On older kernels without getrandom(2), falls back to polling
 * /dev/random for 128-bit entropy (RNDGETENTCNT ioctl or /proc fallback)
 * before reading from /dev/urandom.
 *
 * The Linux path chunks requests at 33,554,431 bytes (getrandom maximum) and
 * retries on EINTR to handle signal interruptions transparently.
 *
 * SECURITY NOTE
 * -------------
 * This function MUST be seeded with genuine OS entropy before it is called
 * for key generation or encapsulation. In virtual machine / container
 * environments at first boot, the kernel entropy pool may be insufficiently
 * seeded. The Linux fallback path mitigates this by blocking on /dev/random
 * until 128 bits of entropy are available. The WASM path relies on the
 * browser to correctly seed the Web Crypto API.
 *
 * Original implementation:
 *   Daan Sprenkels <hello@dsprenkels.com>
 *   MIT License — see license block below.
 *
 * PQClean source: pqclean/common/randombytes.c
 */

/*
 * MIT License
 *
 * Copyright (c) 2017 Daan Sprenkels <hello@dsprenkels.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

/*
 * _GNU_SOURCE must be defined before any includes on Linux to expose
 * SYS_getrandom and the glibc getrandom(2) wrapper.
 */
#if defined(__linux__)
# define _GNU_SOURCE
#endif

#include "randombytes.h"

#if defined(_WIN32)
# include <windows.h>
# include <wincrypt.h>   /* CryptAcquireContext, CryptGenRandom */
#endif

#if defined(__wasi__)
# include <stdlib.h>     /* arc4random_buf */
#endif

#if defined(__linux__)
/*
 * RNDGETENTCNT ioctl number from <linux/random.h>.
 * Inlined here because not every cross-compilation target ships the Linux
 * kernel headers. Used to query the kernel entropy pool size in bits.
 */
# define RNDGETENTCNT 0x80045200

# include <assert.h>
# include <errno.h>
# include <fcntl.h>
# include <poll.h>
# include <stdint.h>
# include <stdio.h>
# include <sys/ioctl.h>
# if defined(__linux__) && defined(__GLIBC__) && \
     ((__GLIBC__ > 2) || (__GLIBC_MINOR__ > 24))
#  define USE_GLIBC
#  include <sys/random.h>   /* getrandom(2) declaration */
# endif
# include <sys/stat.h>
# include <sys/syscall.h>
# include <sys/types.h>
# include <unistd.h>

/* SSIZE_MAX caps the maximum single read from /dev/urandom. */
# if !defined(SSIZE_MAX)
#  define SSIZE_MAX (SIZE_MAX / 2 - 1)
# endif
#endif /* __linux__ */

#if defined(__unix__) || (defined(__APPLE__) && defined(__MACH__))
# include <sys/param.h>
# if defined(BSD)
#  include <stdlib.h>   /* arc4random_buf */
# endif
#endif

#if defined(__EMSCRIPTEN__)
# include <assert.h>
# include <emscripten.h>
# include <errno.h>
# include <stdbool.h>
#endif

/* ── Platform Implementations ───────────────────────────────────────────── */

#if defined(_WIN32)
/**
 * randombytes_win32_randombytes — Windows CryptoAPI implementation.
 *
 * Opens a CryptAcquireContext handle (PROV_RSA_FULL, CRYPT_VERIFYCONTEXT),
 * generates n random bytes via CryptGenRandom, then releases the context.
 * CRYPT_VERIFYCONTEXT avoids persistent key storage (no user key container).
 *
 * @return 0 on success; -1 on any CryptoAPI error.
 */
static int randombytes_win32_randombytes(void *buf, const size_t n) {
    HCRYPTPROV ctx;
    BOOL tmp;

    tmp = CryptAcquireContext(&ctx, NULL, NULL, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT);
    if (tmp == FALSE) {
        return -1;
    }

    tmp = CryptGenRandom(ctx, (unsigned long)n, (BYTE *)buf);
    if (tmp == FALSE) {
        return -1;
    }

    tmp = CryptReleaseContext(ctx, 0);
    if (tmp == FALSE) {
        return -1;
    }

    return 0;
}
#endif /* _WIN32 */

#if defined(__wasi__)
/**
 * randombytes_wasi_randombytes — WASI arc4random_buf implementation.
 *
 * arc4random_buf is available in WASI's libc and draws from the platform's
 * entropy source. Returns 0 (arc4random_buf cannot fail on WASI).
 */
static int randombytes_wasi_randombytes(void *buf, size_t n) {
    arc4random_buf(buf, n);
    return 0;
}
#endif

#if defined(__linux__) && (defined(USE_GLIBC) || defined(SYS_getrandom))
# if defined(USE_GLIBC)
/* getrandom declared via <sys/random.h> */
# elif defined(SYS_getrandom)
/**
 * getrandom — raw syscall wrapper for kernels without glibc getrandom(2).
 * Falls through to the syscall table directly via syscall(SYS_getrandom).
 */
static ssize_t getrandom(void *buf, size_t buflen, unsigned int flags) {
    return syscall(SYS_getrandom, buf, buflen, flags);
}
# endif

/**
 * randombytes_linux_randombytes_getrandom — getrandom(2) path.
 *
 * Calls getrandom(2) in a loop, chunking at 33,554,431 bytes (the kernel's
 * per-call maximum). Retries on EINTR. Returns -1 on any other error.
 *
 * getrandom(2) blocks on first call until the kernel's CRNG is fully
 * initialized (i.e., sufficient entropy has been gathered at boot). After
 * that it never blocks and never returns a short read (unlike /dev/urandom).
 */
static int randombytes_linux_randombytes_getrandom(void *buf, size_t n) {
    size_t offset = 0, chunk;
    int ret;
    while (n > 0) {
        /* getrandom does not allow chunks larger than 33554431. */
        chunk = n <= 33554431 ? n : 33554431;
        do {
            ret = getrandom((char *)buf + offset, chunk, 0);
        } while (ret == -1 && errno == EINTR);
        if (ret < 0) {
            return ret;
        }
        offset += ret;
        n -= ret;
    }
    assert(n == 0);
    return 0;
}
#endif /* __linux__ && (USE_GLIBC || SYS_getrandom) */

#if defined(__linux__) && !defined(SYS_getrandom)
/**
 * randombytes_linux_read_entropy_ioctl — read kernel entropy count via ioctl.
 *
 * Issues RNDGETENTCNT on the /dev/urandom file descriptor to read the
 * estimated number of bits of entropy in the kernel's input pool.
 */
static int randombytes_linux_read_entropy_ioctl(int device, int *entropy) {
    return ioctl(device, RNDGETENTCNT, entropy);
}

/**
 * randombytes_linux_read_entropy_proc — read kernel entropy count via /proc.
 *
 * Fallback for MIPS and other platforms where the ioctl is not supported.
 * Reads /proc/sys/kernel/random/entropy_avail with fscanf.
 */
static int randombytes_linux_read_entropy_proc(FILE *stream, int *entropy) {
    int retcode;
    do {
        rewind(stream);
        retcode = fscanf(stream, "%d", entropy);
    } while (retcode != 1 && errno == EINTR);
    if (retcode != 1) {
        return -1;
    }
    return 0;
}

/**
 * randombytes_linux_wait_for_entropy — block until kernel has ≥ 128 entropy bits.
 *
 * Polls /dev/random (which blocks until entropy is available) and checks
 * the entropy count via ioctl or /proc. Returns when ≥ 128 bits are
 * available. This prevents reading from /dev/urandom before the kernel's
 * CRNG is seeded (a known risk on embedded/virtual systems at first boot).
 *
 * Uses the IOCTL strategy first; falls back to /proc on ENOTTY/ENOSYS.
 */
static int randombytes_linux_wait_for_entropy(int device) {
    enum { IOCTL, PROC } strategy = IOCTL;
    const int bits = 128;
    struct pollfd pfd;
    int fd;
    FILE *proc_file;
    int retcode, retcode_error = 0;
    int entropy = 0;

    retcode = randombytes_linux_read_entropy_ioctl(device, &entropy);
    if (retcode != 0 && (errno == ENOTTY || errno == ENOSYS)) {
        /* ioctl unsupported — fall back to /proc. */
        strategy = PROC;
        proc_file = fopen("/proc/sys/kernel/random/entropy_avail", "r");
    } else if (retcode != 0) {
        return -1;
    }
    if (entropy >= bits) {
        return 0;   /* Already sufficient entropy; no need to block. */
    }

    do {
        fd = open("/dev/random", O_RDONLY);
    } while (fd == -1 && errno == EINTR);
    if (fd == -1) {
        return -1;
    }

    pfd.fd = fd;
    pfd.events = POLLIN;
    for (;;) {
        retcode = poll(&pfd, 1, -1);
        if (retcode == -1 && (errno == EINTR || errno == EAGAIN)) {
            continue;
        } else if (retcode == 1) {
            if (strategy == IOCTL) {
                retcode = randombytes_linux_read_entropy_ioctl(device, &entropy);
            } else if (strategy == PROC) {
                retcode = randombytes_linux_read_entropy_proc(proc_file, &entropy);
            } else {
                return -1;
            }

            if (retcode != 0) {
                retcode_error = retcode;
                break;
            }
            if (entropy >= bits) {
                break;
            }
        } else {
            retcode_error = -1;
            break;
        }
    }
    do {
        retcode = close(fd);
    } while (retcode == -1 && errno == EINTR);
    if (strategy == PROC) {
        do {
            retcode = fclose(proc_file);
        } while (retcode == -1 && errno == EINTR);
    }
    if (retcode_error != 0) {
        return retcode_error;
    }
    return retcode;
}

/**
 * randombytes_linux_randombytes_urandom — /dev/urandom fallback path.
 *
 * Opens /dev/urandom, waits for ≥ 128 bits of kernel entropy via
 * randombytes_linux_wait_for_entropy, then reads n bytes in a loop
 * (retrying on EAGAIN/EINTR). Used only on Linux kernels that predate
 * the getrandom(2) syscall (Linux < 3.17).
 */
static int randombytes_linux_randombytes_urandom(void *buf, size_t n) {
    int fd;
    size_t offset = 0, count;
    ssize_t tmp;
    do {
        fd = open("/dev/urandom", O_RDONLY);
    } while (fd == -1 && errno == EINTR);
    if (fd == -1) {
        return -1;
    }
    if (randombytes_linux_wait_for_entropy(fd) == -1) {
        return -1;
    }

    while (n > 0) {
        count = n <= SSIZE_MAX ? n : SSIZE_MAX;
        tmp = read(fd, (char *)buf + offset, count);
        if (tmp == -1 && (errno == EAGAIN || errno == EINTR)) {
            continue;
        }
        if (tmp == -1) {
            return -1;
        }
        offset += tmp;
        n -= tmp;
    }
    close(fd);
    assert(n == 0);
    return 0;
}
#endif /* __linux__ && !SYS_getrandom */

#if defined(BSD)
/**
 * randombytes_bsd_randombytes — arc4random_buf implementation (BSD).
 *
 * arc4random_buf is the preferred CSPRNG on all BSD-family systems
 * (FreeBSD, NetBSD, OpenBSD, macOS). It is automatically reseeded from
 * the kernel and cannot return an error. Returns 0 always.
 */
static int randombytes_bsd_randombytes(void *buf, size_t n) {
    arc4random_buf(buf, n);
    return 0;
}
#endif /* BSD */

#if defined(__EMSCRIPTEN__)
/**
 * randombytes_js_randombytes — Web Crypto API implementation (Emscripten).
 *
 * Calls crypto.getRandomValues() from inside EM_ASM_INT, writing the result
 * directly into the WASM linear memory buffer. Tries globalThis.crypto,
 * then self.crypto, then window.crypto to cover main thread, Web Workers,
 * and legacy environments.
 *
 * Sets errno = EINVAL and returns -1 if no crypto object is available
 * (e.g., an insecure HTTP context).
 */
static int randombytes_js_randombytes(void *buf, size_t n) {
    const int ret = EM_ASM_INT({
        try {
            /*
             * Try globalThis.crypto first (ES2020+, works in main thread,
             * Web Workers, and Service Workers). Fall back to self.crypto
             * (Web Workers) and window.crypto (legacy browsers).
             */
            var crypto = (typeof globalThis !== 'undefined' && globalThis.crypto)
                          || (typeof self !== 'undefined' && self.crypto)
                          || (typeof window !== 'undefined' && window.crypto);
            var ua = new Uint8Array($1);
            crypto.getRandomValues(ua);
            writeArrayToMemory(ua, $0);
            return 0;
        } catch (error) {
            return -1;
        }
    }, buf, n);
    if (ret == 0) return 0;
    errno = EINVAL;
    return -1;
}
#endif /* __EMSCRIPTEN__ */

/* ── Public Interface ────────────────────────────────────────────────────── */

/**
 * randombytes — fill a buffer with cryptographically secure random bytes.
 *
 * Dispatches to the appropriate platform implementation at compile time.
 * Exactly one branch will be compiled in; the others are dead-stripped.
 *
 * @param[out] output  Buffer to fill with random bytes.
 * @param[in]  n       Number of bytes to generate.
 * @return 0 on success; -1 on CSPRNG failure (platform-dependent).
 *
 * IMPORTANT: Callers in kem.c propagate a non-zero return as a key
 * generation or encapsulation failure. The caller is responsible for
 * NOT using the output buffer if this function returns non-zero.
 */
int randombytes(uint8_t *output, size_t n) {
    void *buf = (void *)output;
#if defined(__EMSCRIPTEN__)
    /* Primary target: WASM/browser — use Web Crypto API. */
    return randombytes_js_randombytes(buf, n);
#elif defined(__linux__)
# if defined(USE_GLIBC)
    return randombytes_linux_randombytes_getrandom(buf, n);
# elif defined(SYS_getrandom)
    return randombytes_linux_randombytes_getrandom(buf, n);
# else
    return randombytes_linux_randombytes_urandom(buf, n);
# endif
#elif defined(BSD)
    return randombytes_bsd_randombytes(buf, n);
#elif defined(_WIN32)
    return randombytes_win32_randombytes(buf, n);
#elif defined(__wasi__)
    return randombytes_wasi_randombytes(buf, n);
#else
# error "randombytes(...) is not supported on this platform"
#endif
}
