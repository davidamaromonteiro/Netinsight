<?php
/**
 * ACME Store - Product Detail
 * VULNERABLE: SQL injection in id parameter
 */
error_reporting(0);
ini_set('display_errors', 0);
mysqli_report(MYSQLI_REPORT_OFF);

$host = getenv('MYSQL_HOST') ?: 'acme-mysql';
$user = getenv('MYSQL_USER') ?: 'acme_app';
$pass = getenv('MYSQL_PASSWORD') ?: 'AcmeDB#P@ss!2024';
$db   = getenv('MYSQL_DATABASE') ?: 'acme';

$conn = new mysqli($host, $user, $pass, $db);
$id = $_GET['id'] ?? '1';

// VULNERABLE: Direct interpolation of user input
$sql = "SELECT * FROM products WHERE id = $id";
$result = $conn->query($sql);
$product = $result ? $result->fetch_assoc() : null;
$error = $conn->error;
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title><?= $product ? htmlspecialchars($product['name']) : 'Product' ?> - ACME Store</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        header { background: linear-gradient(135deg, #1a365d, #2b6cb0); color: white; padding: 1rem 2rem; }
        nav { background: #2d3748; padding: 0.5rem 2rem; }
        nav a { color: #a0aec0; text-decoration: none; margin-right: 1.5rem; font-size: 0.9rem; }
        .container { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
        .product { background: white; border-radius: 8px; padding: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .product h1 { font-size: 1.8rem; margin-bottom: 1rem; }
        .product .price { font-size: 2rem; color: #2b6cb0; font-weight: bold; margin-bottom: 1rem; }
        .product .meta { display: flex; gap: 2rem; color: #718096; font-size: 0.9rem; margin-bottom: 1.5rem; }
        .product .description { line-height: 1.6; color: #4a5568; }
        .back { display: inline-block; margin-top: 1.5rem; color: #2b6cb0; text-decoration: none; }
        .error { background: #fed7d7; color: #c53030; padding: 1rem; border-radius: 6px; margin-bottom: 1rem; font-family: monospace; font-size:0.85rem; }
    </style>
</head>
<body>
    <header><h1>🏪 ACME Store</h1></header>
    <nav>
        <a href="index.php">Products</a>
        <a href="login.php">Login</a>
        <a href="admin.php">Admin</a>
    </nav>
    <div class="container">
        <?php if ($error): ?>
        <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>
        
        <?php if ($product): ?>
        <div class="product">
            <h1><?= htmlspecialchars($product['name']) ?></h1>
            <div class="price">$<?= number_format($product['price'], 2) ?></div>
            <div class="meta">
                <span>📦 <?= $product['stock'] ?> in stock</span>
                <span>🏷️ <?= htmlspecialchars($product['category']) ?></span>
                <span>🆔 #<?= $product['id'] ?></span>
            </div>
            <div class="description"><?= nl2br(htmlspecialchars($product['description'])) ?></div>
            <a href="index.php" class="back">← Back to products</a>
        </div>
        <?php else: ?>
        <p>Product not found.</p>
        <?php endif; ?>
    </div>
</body>
</html>
<?php $conn->close(); ?>
