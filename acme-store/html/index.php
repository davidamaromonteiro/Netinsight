<?php
/**
 * ACME Store - Product Listing
 * VULNERABLE: SQL injection in category/search parameters
 */
error_reporting(0);
ini_set('display_errors', 0);
mysqli_report(MYSQLI_REPORT_OFF);

$host = getenv('MYSQL_HOST') ?: 'acme-mysql';
$user = getenv('MYSQL_USER') ?: 'acme_app';
$pass = getenv('MYSQL_PASSWORD') ?: 'AcmeDB#P@ss!2024';
$db   = getenv('MYSQL_DATABASE') ?: 'acme';

$conn = new mysqli($host, $user, $pass, $db);
$category = $_GET['category'] ?? '';
$search   = $_GET['search'] ?? '';

// VULNERABLE: Direct string interpolation - no prepared statements
$sql = "SELECT * FROM products WHERE 1=1";
if ($category) {
    $sql .= " AND category = '$category'";  // SQLi here
}
if ($search) {
    $sql .= " AND (name LIKE '%$search%' OR description LIKE '%$search%')";  // SQLi here
}
$sql .= " ORDER BY name";

$result = $conn->query($sql);
$error = $conn->error;
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACME Store - Products</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        header { background: linear-gradient(135deg, #1a365d, #2b6cb0); color: white; padding: 1rem 2rem; }
        header h1 { font-size: 1.5rem; }
        nav { background: #2d3748; padding: 0.5rem 2rem; }
        nav a { color: #a0aec0; text-decoration: none; margin-right: 1.5rem; font-size: 0.9rem; }
        nav a:hover { color: white; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .search-bar { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        .search-bar input, .search-bar select, .search-bar button { padding: 0.5rem 1rem; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 0.9rem; }
        .search-bar button { background: #2b6cb0; color: white; border: none; cursor: pointer; }
        .products { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }
        .product-card { background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .product-card h3 { font-size: 1.1rem; margin-bottom: 0.5rem; }
        .product-card .category { font-size: 0.75rem; color: #718096; text-transform: uppercase; margin-bottom: 0.5rem; }
        .product-card .price { font-size: 1.5rem; color: #2b6cb0; font-weight: bold; }
        .product-card .stock { font-size: 0.8rem; color: #a0aec0; }
        .product-card a { display: inline-block; margin-top: 0.75rem; color: #2b6cb0; text-decoration: none; font-weight: 500; }
        .error { background: #fed7d7; color: #c53030; padding: 1rem; border-radius: 6px; margin-bottom: 1rem; font-family: monospace; font-size: 0.85rem; }
    </style>
</head>
<body>
    <header>
        <h1>🏪 ACME Store</h1>
    </header>
    <nav>
        <a href="index.php">Products</a>
        <a href="login.php">Login</a>
        <a href="admin.php">Admin</a>
    </nav>
    <div class="container">
        <h2 style="margin-bottom:1rem">Our Products</h2>
        
        <?php if ($error): ?>
        <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <form class="search-bar" method="GET">
            <input type="text" name="search" placeholder="Search products..." value="<?= htmlspecialchars($search) ?>">
            <select name="category">
                <option value="">All Categories</option>
                <option value="Widgets" <?= $category==='Widgets'?'selected':'' ?>>Widgets</option>
                <option value="Gadgets" <?= $category==='Gadgets'?'selected':'' ?>>Gadgets</option>
                <option value="Accessories" <?= $category==='Accessories'?'selected':'' ?>>Accessories</option>
                <option value="Smart Home" <?= $category==='Smart Home'?'selected':'' ?>>Smart Home</option>
                <option value="Electronics" <?= $category==='Electronics'?'selected':'' ?>>Electronics</option>
            </select>
            <button type="submit">Search</button>
        </form>

        <div class="products">
            <?php if ($result && $result->num_rows > 0): ?>
                <?php while($row = $result->fetch_assoc()): ?>
                <div class="product-card">
                    <div class="category"><?= htmlspecialchars($row['category']) ?></div>
                    <h3><?= htmlspecialchars($row['name']) ?></h3>
                    <div class="price">$<?= number_format($row['price'], 2) ?></div>
                    <div class="stock"><?= $row['stock'] ?> in stock</div>
                    <a href="product.php?id=<?= $row['id'] ?>">View Details →</a>
                </div>
                <?php endwhile; ?>
            <?php else: ?>
                <p>No products found.</p>
            <?php endif; ?>
        </div>

        <!-- DEBUG: SQL query (visible in page source) -->
        <!-- <?= $sql ?> -->
    </div>
</body>
</html>
<?php $conn->close(); ?>
