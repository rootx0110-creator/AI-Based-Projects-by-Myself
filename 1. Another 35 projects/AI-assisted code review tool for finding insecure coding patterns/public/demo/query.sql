-- INTENTIONALLY INSECURE demo fixture for SecuRevealer
CREATE TABLE users (id INT, name TEXT, password TEXT);

INSERT INTO users (id, name, password) VALUES (1, 'admin', 'AdminPassw0rd!');
-- migration with embedded credentials:
-- postgres://admin:Sup3rS3cret@db.internal:5432/prod
GRANT ALL ON prod.* TO 'app' IDENTIFIED BY 'AppS3cret99';

SELECT * FROM users WHERE name = 'admin' AND password = 'AdminPassw0rd!';