-- ACME Store - Test Database
-- Intentionally vulnerable for SQL injection testing
CREATE DATABASE IF NOT EXISTS acme;
USE acme;

-- Users table (vulnerable: plain-text passwords)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'customer') DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    stock INT DEFAULT 0,
    image VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    product_id INT,
    quantity INT DEFAULT 1,
    total_price DECIMAL(10,2),
    credit_card VARCHAR(19),
    address TEXT,
    status ENUM('pending', 'shipped', 'delivered') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Secrets table (hidden data for pentesting)
CREATE TABLE secrets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    value TEXT,
    note VARCHAR(255)
);

-- ═══════════════════════════════════════════
-- SEED DATA
-- ═══════════════════════════════════════════

-- Users (passwords in plaintext - intentionally vulnerable)
INSERT INTO users (username, password, email, role) VALUES
('admin', 'Acme@dm1n#2024!', 'admin@acme-store.local', 'admin'),
('jsmith', 'password123', 'john.smith@email.com', 'customer'),
('mwilson', 'letmein', 'mary.wilson@email.com', 'customer'),
('rbrown', 'qwerty', 'robert.brown@email.com', 'customer'),
('ldavis', '123456', 'lisa.davis@email.com', 'customer');

-- Products
INSERT INTO products (name, description, price, category, stock, image) VALUES
('Widget Pro X1', 'Professional grade widget with titanium coating', 299.99, 'Widgets', 45, '/img/widget-x1.jpg'),
('Widget Basic B2', 'Entry-level widget for everyday use', 49.99, 'Widgets', 200, '/img/widget-b2.jpg'),
('GadgetMaster 3000', 'Multi-function gadget with AI capabilities', 899.00, 'Gadgets', 12, '/img/gadget-3000.jpg'),
('GadgetMini', 'Pocket-sized gadget, perfect for travel', 129.50, 'Gadgets', 78, '/img/gadget-mini.jpg'),
('SuperCable USB-C', 'Braided USB-C cable, 2m, 100W PD', 24.99, 'Accessories', 500, '/img/cable-usbc.jpg'),
('Wireless Charger Pad', '15W fast wireless charging pad', 39.99, 'Accessories', 150, '/img/charger-pad.jpg'),
('SmartLock Door', 'Biometric smart door lock with WiFi', 249.00, 'Smart Home', 30, '/img/smartlock.jpg'),
('ThermoStat Pro', 'AI-powered thermostat, saves 30% energy', 189.00, 'Smart Home', 25, '/img/thermostat.jpg'),
('DroneX Explorer', '4K camera drone, 30min flight time', 599.99, 'Electronics', 8, '/img/drone-x.jpg'),
('NoiseCancel Pro', 'Active noise cancelling headphones', 279.00, 'Electronics', 60, '/img/headphones.jpg');

-- Orders (with realistic credit card data for pentesting)
INSERT INTO orders (user_id, product_id, quantity, total_price, credit_card, address, status) VALUES
(2, 1, 1, 299.99, '4532-7890-1234-5678', '123 Main St, Springfield, IL 62701', 'delivered'),
(2, 5, 3, 74.97, '4532-7890-1234-5678', '123 Main St, Springfield, IL 62701', 'shipped'),
(3, 3, 1, 899.00, '5214-9876-5432-1098', '456 Oak Ave, Portland, OR 97201', 'delivered'),
(3, 8, 1, 189.00, '5214-9876-5432-1098', '456 Oak Ave, Portland, OR 97201', 'pending'),
(4, 10, 2, 558.00, '3782-8224-6310-005', '789 Pine Rd, Austin, TX 73301', 'shipped'),
(5, 2, 1, 49.99, '6011-1111-2222-3333', '321 Elm St, Denver, CO 80201', 'delivered'),
(5, 6, 2, 79.98, '6011-1111-2222-3333', '321 Elm St, Denver, CO 80201', 'delivered');

-- Secrets (flags for pentesting)
INSERT INTO secrets (name, value, note) VALUES
('admin_api_key', 'acme-api-7f3a9b2c-4d1e-5f6a-8b9c-0d1e2f3a4b5c', 'Used for internal API authentication'),
('db_credentials', 'mysql://acme_app:AcmeDB#P@ss!2024@localhost:3306/acme', 'Production database credentials'),
('backup_server', '10.0.99.200', 'Offsite backup server IP'),
('flag_ctf', 'FLAG{sql_injection_is_still_the_king}', 'CTF flag for SQL injection challenge'),
('encryption_key', 'AES256-KEY-8a7b6c5d4e3f2a1b', 'Legacy encryption key - DO NOT USE IN PROD');
