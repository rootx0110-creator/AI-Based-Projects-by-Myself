<?php
// ⚠️ DELIBERATELY VULNERABLE — DO NOT DEPLOY
// Detects: OS Command Injection

$host = $_GET['host'];
$out  = shell_exec("ping -c 1 " . $host);   // ← CWE-78
echo "<pre>$out</pre>";

// Additional: using system() with input
$file = $_GET['file'];
system("cat " . $file);                     // ← another sink

// Backtick operator (equivalent to shell_exec)
$who = $_GET['user'];
$result = `whoami $who`;                    // ← backtick sink
echo $result;
?>