CREATE DATABASE IF NOT EXISTS berceau_prod
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'berceau_app'@'localhost' IDENTIFIED BY 'BerceauApp@2026!';
CREATE USER IF NOT EXISTS 'berceau_app'@'127.0.0.1' IDENTIFIED BY 'BerceauApp@2026!';

GRANT ALL PRIVILEGES ON berceau_prod.* TO 'berceau_app'@'localhost';
GRANT ALL PRIVILEGES ON berceau_prod.* TO 'berceau_app'@'127.0.0.1';
FLUSH PRIVILEGES;
