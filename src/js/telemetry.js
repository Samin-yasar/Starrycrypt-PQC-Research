// Domain-restricted benchmark submission via Supabase Edge Function
const EDGE_FUNCTION_URL = 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/benchmark-submit';
const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';

/**
 * Uploads benchmark results via Edge Function (domain-restricted).
 * 
 * @param {string} implementation - "wasm" or "pure-js"
 * @param {object} result - The statistical result object from runBenchmarkN
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

// Deprecated: Direct Supabase insert (kept for reference during migration)
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
