<?php
/**
 * ACME Store - Admin Panel
 * VULNERABLE: No proper session validation, SQLi in search
 */
error_reporting(0);
ini_set('display_errors', 0);
mysqli_report(MYSQLI_REPORT_OFF);

session_start();
$host = getenv('MYSQL_HOST') ?: 'acme-mysql';
$user = getenv('MYSQL_USER') ?: 'acme_app';
$pass = getenv('MYSQL_PASSWORD') ?: 'AcmeDB#P@ss!2024';
$db   = getenv('MYSQL_DATABASE') ?: 'acme';

$conn = new mysqli($host, $user, $pass, $db);

// Weak auth check
$loggedIn = isset($_SESSION['user']);

$searchUser = $_GET['user'] ?? '';
$table = $_GET['table'] ?? '';
$users = [];
$orders = [];
$secrets = [];

if ($loggedIn) {
    // VULNERABLE: SQLi in user search
    if ($searchUser) {
        $sql = "SELECT * FROM users WHERE username LIKE '%$searchUser%'";
        $result = $conn->query($sql);
        $users = $result ? $result->fetch_all(MYSQLI_ASSOC) : [];
    }
    
    // VULNERABLE: table name from user input
    if ($table) {
        $sql = "SELECT * FROM $table LIMIT 20";
        $result = $conn->query($sql);
        if ($result) {
            if ($table === 'orders') $orders = $result->fetch_all(MYSQLI_ASSOC);
            if ($table === 'secrets') $secrets = $result->fetch_all(MYSQLI_ASSOC);
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin - ACME Store</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        header { background: linear-gradient(135deg, #1a365d, #2b6cb0); color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 1.2rem; }
        nav { background: #2d3748; padding: 0.5rem 2rem; }
        nav a { color: #a0aec0; text-decoration: none; margin-right: 1.5rem; font-size: 0.9rem; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .panel { background: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .panel h2 { font-size: 1.1rem; margin-bottom: 1rem; color: #2d3748; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f7fafc; font-weight: 600; }
        .search { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .search input { flex:1; padding: 0.5rem; border:1px solid #cbd5e0; border-radius:6px; }
        .search button { padding: 0.5rem 1rem; background: #2b6cb0; color: white; border: none; border-radius: 6px; cursor: pointer; }
        .tabs { display: flex; gap: 0.25rem; margin-bottom: 1rem; }
        .tabs a { padding: 0.4rem 1rem; border-radius: 6px; text-decoration: none; font-size: 0.85rem; color: #4a5568; background: #edf2f7; }
        .tabs a.active { background: #2b6cb0; color: white; }
        .logout { color: white; text-decoration: none; font-size: 0.85rem; }
        .badge { padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
        .badge-admin { background: #c6f6d5; color: #22543d; }
        .badge-customer { background: #bee3f8; color: #2a4365; }
    </style>
</head>
<body>
    <header>
        <h1>⚙️ ACME Store - Admin Panel</h1>
        <?php if ($loggedIn): ?>
        <a href="?logout=1" class="logout">Logout (<?= htmlspecialchars($_SESSION['user']['username']) ?>)</a>
        <?php endif; ?>
    </header>
    <nav>
        <a href="index.php">Products</a>
        <a href="login.php">Login</a>
        <a href="admin.php">Admin</a>
    </nav>
    <div class="container">
        <?php if (!$loggedIn): ?>
        <div class="panel">
            <h2>Access Denied</h2>
            <p>Please <a href="login.php">login</a> to access the admin panel.</p>
        </div>
        <?php else: ?>
        
        <!-- User Search (SQLi) -->
        <div class="panel">
            <h2>👥 User Management</h2>
            <form class="search" method="GET">
                <input type="text" name="user" placeholder="Search users..." value="<?= htmlspecialchars($searchUser) ?>">
                <input type="hidden" name="table" value="<?= htmlspecialchars($table) ?>">
                <button type="submit">Search</button>
            </form>
            <?php if ($users): ?>
            <table>
                <tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Created</th></tr>
                <?php foreach($users as $u): ?>
                <tr>
                    <td><?= $u['id'] ?></td>
                    <td><?= htmlspecialchars($u['username']) ?></td>
                    <td><?= htmlspecialchars($u['email']) ?></td>
                    <td><span class="badge badge-<?= $u['role'] ?>"><?= $u['role'] ?></span></td>
                    <td><?= $u['created_at'] ?></td>
                </tr>
                <?php endforeach; ?>
            </table>
            <?php endif; ?>
        </div>

        <!-- Data Browser (SQLi via table name) -->
        <div class="panel">
            <h2>📊 Data Browser</h2>
            <div class="tabs">
                <a href="?table=orders" class="<?= $table==='orders'?'active':'' ?>">Orders</a>
                <a href="?table=secrets" class="<?= $table==='secrets'?'active':'' ?>">Secrets</a>
                <a href="?table=products" class="<?= $table==='products'?'active':'' ?>">Products</a>
            </div>
            
            <?php if ($orders): ?>
            <table>
                <tr><th>ID</th><th>User</th><th>Product</th><th>Qty</th><th>Total</th><th>Credit Card</th><th>Address</th><th>Status</th></tr>
                <?php foreach($orders as $o): ?>
                <tr>
                    <td><?= $o['id'] ?></td>
                    <td><?= $o['user_id'] ?></td>
                    <td><?= $o['product_id'] ?></td>
                    <td><?= $o['quantity'] ?></td>
                    <td>$<?= $o['total_price'] ?></td>
                    <td style="font-family:monospace"><?= htmlspecialchars($o['credit_card']) ?></td>
                    <td><?= htmlspecialchars(substr($o['address'], 0, 30)) ?></td>
                    <td><?= $o['status'] ?></td>
                </tr>
                <?php endforeach; ?>
            </table>
            <?php endif; ?>

            <?php if ($secrets): ?>
            <table>
                <tr><th>ID</th><th>Name</th><th>Value</th><th>Note</th></tr>
                <?php foreach($secrets as $s): ?>
                <tr>
                    <td><?= $s['id'] ?></td>
                    <td><?= htmlspecialchars($s['name']) ?></td>
                    <td style="font-family:monospace;color:#c53030"><?= htmlspecialchars($s['value']) ?></td>
                    <td><?= htmlspecialchars($s['note']) ?></td>
                </tr>
                <?php endforeach; ?>
            </table>
            <?php endif; ?>
        </div>
        <?php endif; ?>
    </div>
</body>
</html>
<?php 
if (isset($_GET['logout'])) {
    session_destroy();
    header('Location: login.php');
    exit;
}
$conn->close(); 
?>
