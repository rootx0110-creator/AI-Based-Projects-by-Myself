'use strict';
// INTENTIONALLY INSECURE demo fixture for SecuRevealer — do not use in production.
const express = require('express');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const { exec } = require('child_process');
const app = express();

const JWT_SECRET = 's3cr3t_key_do_not_share_123';     // hardcoded secret
const AWS_KEY = 'AKIAIOSFODNN7EXAMPLE';              // hardcoded AWS access key id

app.use(cors({ origin: '*', credentials: true }));   // wildcard CORS

app.get('/user', (req, res) => {
  db.query('SELECT * FROM users WHERE id = ' + req.query.id);   // SQL injection
  res.send('ok');
});

app.post('/convert', (req, res) => {
  exec('convert ' + req.body.image + ' out.png');               // command injection
});

app.get('/greet', (req, res) => {
  document.getElementById('out').innerHTML = req.query.name;    // XSS sink
  eval(req.query.expr);                                          // code injection
});

app.get('/hash', (req, res) => {
  const h = crypto.createHash('md5').update(req.query.pw).digest('hex');  // weak hash
  const token = Math.random().toString(36);                     // insecure random
  res.send(h + token);
});

app.get('/fetch', (req, res) => {
  fetch(req.body.url).then(r => r.text()).then(t => res.send(t)); // SSRF
  https.get('http://api.internal/health', { rejectUnauthorized: false }); // TLS off + plaintext
});

app.get('/jump', (req, res) => res.redirect(req.query.next));    // open redirect

app.get('/file', (req, res) => {
  fs.readFile(path.join(__dirname, req.query.name), (e, d) => res.send(d)); // path traversal
});

jwt.verify(token, JWT_SECRET, { algorithms: ['none'] });         // JWT none alg

app.listen(3000);