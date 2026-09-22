<?php
// ⚠️ DELIBERATELY VULNERABLE — DO NOT DEPLOY
// Detects: SQL Injection via string concatenation

$mysqli = new mysqli("localhost", "app", "app", "appdb");

$id = $_GET['id'];                          // ← untrusted input
$q  = "SELECT * FROM users WHERE id = " . $id;   // ← CWE-89
$res = $mysqli->query($q);

while ($row = $res->fetch_assoc()) {
    echo htmlspecialchars($row['username']);
}

// Additional vulnerable pattern: login bypass
$user = $_POST['user'];
$pass = $_POST['pass'];
$sql  = "SELECT * FROM users WHERE user='$user' AND pass='$pass'";
$r    = $mysqli->query($sql);
if ($r && $r->num_rows > 0) { echo "Welcome!"; }
?>