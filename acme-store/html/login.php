<?php
/**
 * ACME Store - Login
 * VULNERABLE: SQL injection in both username and password fields
 */
error_reporting(0);
ini_set('display_errors', 0);
mysqli_report(MYSQLI_REPORT_OFF);

session_start();
$host = getenv('MYSQL_HOST') ?: 'acme-mysql';
$user = getenv('MYSQL_USER') ?: 'acme_app';
$pass = getenv('MYSQL_PASSWORD') ?: 'AcmeDB#P@ss!2024';
$db   = getenv('MYSQL_DATABASE') ?: 'acme';

$error = '';
$conn = new mysqli($host, $user, $pass, $db);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';
    
    // VULNERABLE: SQL injection in authentication query
    $sql = "SELECT * FROM users WHERE username = '$username' AND password = '$password'";
    $result = $conn->query($sql);
    
    if ($result && $result->num_rows > 0) {
        $userData = $result->fetch_assoc();
        $_SESSION['user'] = $userData;
        header('Location: admin.php');
        exit;
    } else {
        $error = "Invalid credentials. SQL: $sql";
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login - ACME Store</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a365d, #2b6cb0); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-box { background: white; border-radius: 12px; padding: 2.5rem; width: 380px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        .login-box h1 { text-align: center; margin-bottom: 0.5rem; color: #1a365d; }
        .login-box p { text-align: center; color: #718096; margin-bottom: 2rem; font-size: 0.9rem; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.25rem; font-size: 0.85rem; color: #4a5568; font-weight: 500; }
        .form-group input { width: 100%; padding: 0.6rem 0.8rem; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 0.95rem; }
        button { width: 100%; padding: 0.75rem; background: #2b6cb0; color: white; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; font-weight: 500; margin-top: 0.5rem; }
        button:hover { background: #1a4971; }
        .error { background: #fed7d7; color: #c53030; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem; word-break: break-all; }
        .back { text-align: center; margin-top: 1rem; }
        .back a { color: #2b6cb0; text-decoration: none; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔐 Login</h1>
        <p>ACME Store Administration</p>
        
        <?php if ($error): ?>
        <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" placeholder="Enter username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter password" required>
            </div>
            <button type="submit">Sign In</button>
        </form>
        <div class="back"><a href="index.php">← Back to store</a></div>
    </div>
</body>
</html>
<?php $conn->close(); ?>
