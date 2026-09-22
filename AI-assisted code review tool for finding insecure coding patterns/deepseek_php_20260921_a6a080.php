<?php
// ⚠️ DELIBERATELY VULNERABLE — DO NOT DEPLOY
// Detects: Reflected + Stored XSS

// Reflected XSS
$name = $_GET['name'];
echo "<h1>Hello, $name</h1>";               // ← CWE-79 (unescaped output)

// Stored XSS
$comment = $_POST['comment'];
file_put_contents("comments.txt", $comment . "\n", FILE_APPEND);

// Later display
foreach (file("comments.txt") as $c) {
    echo "<div class='comment'>$c</div>";   // ← Stored XSS sink
}
?>