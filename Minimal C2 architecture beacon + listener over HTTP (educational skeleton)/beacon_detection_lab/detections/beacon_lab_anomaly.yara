/*
    Beacon Detection Lab - educational YARA rule
    --------------------------------------------
    Defensive artifact: targets common traits of tiny HTTP polling
    scripts dropped to disk (scheduled check-in loops), to help blue
    teams catalog such samples. Meant for lab/teaching use - expect
    false positives against legitimate updaters and monitoring agents.
*/

rule Beacon_Lab_Small_Periodic_HTTP_Script
{
    meta:
        author      = "Beacon Detection Lab (educational)"
        description = "Small script/binary containing an HTTP check-in loop with sleep-based periodicity"
        purpose     = "education / blue-team cataloging"
        date        = "2026-09-19"
        confidence  = "low"
        caveat      = "Broad heuristics - will match legitimate polling tools"

    strings:
        // HTTP client construction / request strings
        $http1 = "POST /" ascii
        $http2 = "GET /" ascii
        $http3 = "User-Agent" ascii nocase
        $http4 = "Content-Type: application/x-www-form-urlencoded" ascii nocase

        // Periodicity hints
        $sleep1 = "sleep" ascii nocase
        $sleep2 = "time.sleep" ascii
        $sleep3 = "Start-Sleep" ascii nocase
        $sleep4 = "timeout" ascii nocase

        // Loop + retry behavior
        $loop1 = "while" ascii nocase
        $loop2 = "retry" ascii nocase

        // Common config blobs in polling tools
        $cfg1 = "interval" ascii nocase
        $cfg2 = "jitter" ascii nocase

    condition:
        uint16(0) == 0x5A4D or uint16(0) == 0x457F or uint16(0) == 0xFEED or
        filesize < 500KB and (
            2 of ($http*) and 1 of ($sleep*) and
            (1 of ($loop*) or 1 of ($cfg*))
        )
}
