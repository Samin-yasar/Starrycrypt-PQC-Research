/**
 * @file telemetry.js
 * @module telemetry
 * @description Benchmark result upload module for the Starrycrypt PQC Research project.
 *
 * OVERVIEW
 * --------
 * Provides uploadBenchmark(), a function that submits a completed benchmark
 * result object (from runBenchmarkN()) to the Starrycrypt Supabase Edge
 * Function for persistent storage in the pqc_benchmarks table.
 *
 * ARCHITECTURE
 * ------------
 * Browser (this module)
 *   └─ POST JSON → Supabase Edge Function (benchmark-submit)
 *        └─ INSERT → pqc_benchmarks table (server-side validation)
 *
 * Routing via Edge Function rather than direct Supabase client insert provides:
 *   1. Domain restriction — the Edge Function can validate the request origin.
 *   2. Schema validation — the Edge Function sanitizes fields before insert.
 *   3. Rate limiting     — the Edge Function can enforce per-IP submission caps.
 *   4. Key protection    — the anon key is visible in client JS; Edge Function
 *      allows scoped write-only access without exposing service-role keys.
 *
 * PRIVACY
 * -------
 * No personally identifiable information is collected. The result object
 * contains only:
 *   - Anonymous hardware metadata (RAM, core count, OS/browser name, device type).
 *   - Timing statistics aggregated over N runs (mean, stdDev, etc.).
 *   - WASM feature flags (SIMD, threads).
 *   - The full raw JSON result object for research reproducibility.
 * The user-agent string is included for audit/debug purposes only and is
 * not used as a cross-session identifier.
 *
 * CONFIGURATION
 * -------------
 * Replace EDGE_FUNCTION_URL and SUPABASE_ANON_KEY with the values from
 * your Supabase project's Settings > API before deploying.
 *
 * DEPRECATED: uploadBenchmarkDirect() (direct Supabase insert) is kept below
 * for reference during migration. It should not be called in production.
 *
 * @see docs/API.md §Telemetry for the full telemetry API reference.
 * @see supabase/functions/benchmark-submit/ for the Edge Function source.
 */

/** URL of the Supabase Edge Function that accepts benchmark submissions. */
const EDGE_FUNCTION_URL = 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/benchmark-submit';
/** Supabase anonymous (public) key — safe for client-side use with RLS. */
const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';

/**
 * uploadBenchmark — submit a completed benchmark result to the research database.
 *
 * Sends the result object from runBenchmarkN() to the Supabase Edge Function
 * via an authenticated POST request. The Edge Function validates and inserts
 * the data into the pqc_benchmarks table.
 *
 * Returns false (rather than throwing) on network failure or HTTP error to
 * allow the benchmark page to complete without crashing when the user is
 * offline or the Edge Function is temporarily unavailable.
 *
 * @param {'wasm'|'pure-js'} implementation — Which JS implementation was
 *   benchmarked. Written to the `implementation` column in pqc_benchmarks.
 * @param {object} result — The full statistical result object returned by
 *   runBenchmarkN(). Must include a `hardware` key and a `timing` key.
 * @returns {Promise<boolean>} true if the upload succeeded (HTTP 2xx),
 *   false if it failed (network error, non-2xx status, or JSON parse error).
 */
export async function uploadBenchmark(implementation, result) {
    try {
        const response = await fetch(EDGE_FUNCTION_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
            },
            body: JSON.stringify({ implementation, result })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Benchmark upload failed:', response.status, errorData.error || response.statusText);
            return false;
        }

        return true;
    } catch (e) {
        console.error('Failed to upload benchmark:', e);
        return false;
    }
}

/**
 * uploadBenchmarkDirect — DEPRECATED direct Supabase client insert.
 *
 * @deprecated Replaced by uploadBenchmark() which routes through the
 *   Supabase Edge Function for domain restriction and server-side validation.
 *   This function is retained for reference only and MUST NOT be called in
 *   production. It will be removed in a future cleanup.
 *
 * @param {'wasm'|'pure-js'} implementation — Implementation identifier.
 * @param {object} result — runBenchmarkN() result object.
 * @returns {Promise<boolean>} true on successful insert, false on error.
 */
async function uploadBenchmarkDirect(implementation, result) {
    const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2');
    const supabase = createClient('https://YOUR_PROJECT_REF.supabase.co', 'YOUR_SUPABASE_ANON_KEY');
    
    try {
        const { error } = await supabase.from('pqc_benchmarks').insert({
            implementation,
            ram_gib: result.hardware?.ramGiB || null,
            logical_cores: result.hardware?.logicalCores || null,
            os_name: result.hardware?.osName || null,
            os_version: result.hardware?.osVersion || null,
            browser_name: result.hardware?.browserName || null,
            browser_version: result.hardware?.browserVersion || null,
            device_type: result.hardware?.deviceType || null,
            device_model: result.hardware?.deviceModel || null,
            platform: result.hardware?.platform || null,
            user_agent: result.hardware?.userAgent || null,
            total_handshake_mean: result.timing?.totalHandshakeMs?.mean || null,
            mlkem_keygen_mean: result.timing?.mlkemKeyGenMs?.mean || null,
            mlkem_encaps_mean: result.timing?.mlkemEncapsMs?.mean || null,
            mlkem_decaps_mean: result.timing?.mlkemDecapsMs?.mean || null,
            raw_json: result
        });

        if (error) {
            console.error('Supabase insert failed:', error.code, '|', error.message);
            return false;
        }
        return true;
    } catch (e) {
        console.error('Failed to upload benchmark:', e);
        return false;
    }
}
