<?php
// INTENTIONALLY INSECURE demo fixture for SecuRevealer — do not use in production.
$dsn = "mysql://root:S3cr3tP@ss@localhost/shop";     // credentials in connection string

$id = $_GET['id'];
$result = mysql_query("SELECT * FROM users WHERE id = " . $id);   // SQL injection

exec("ping -c 1 " . $_GET['host']);                  // command injection
include($_GET['page']);                              // local/remote file inclusion
eval($_POST['code']);                                // arbitrary code execution

$password = "Hunter2Password!";                      // hardcoded password
$token = md5($_GET['user'] . time());                // weak hash for token
$xml = simplexml_load_string($_GET['xmlbody']);      // XXE candidate

echo unserialize($_COOKIE['cart']);                  // unsafe deserialization
?>