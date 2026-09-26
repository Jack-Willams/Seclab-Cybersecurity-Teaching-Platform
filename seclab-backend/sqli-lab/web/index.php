<?php
// ════════════════════════════════════════════════════════════════
//  ByteShop SQLi Challenge – 真实 SQL 注入训练靶场 (Light Mode)
//  Three levels: String / UNION / Login-Bypass
// ════════════════════════════════════════════════════════════════
header('Content-Type: text/html; charset=utf-8');

$host   = "db";
$dbuser = "root";
$dbpass = "123456";
$dbname = "sqli_lab";

// ── 等待 MySQL 就绪（最多重试 10 次，每次 1 秒）──────────────────
$conn = null;
for ($retry = 0; $retry < 10; $retry++) {
    $conn = @new mysqli($host, $dbuser, $dbpass, $dbname);
    if (!$conn->connect_error) break;
    sleep(1);
}
if ($conn->connect_error) {
    die('<div style="font:14px monospace;color:#dc2626;padding:20px">DB Error: ' . htmlspecialchars($conn->connect_error) . '</div>');
}
$conn->set_charset('utf8mb4');

// ── 自动初始化数据库（保底措施：兼容已有 volume 无需重建容器）──
function ensureDbInitialized(mysqli $conn): void {
    // 1. 建表
    $conn->query("CREATE TABLE IF NOT EXISTS users (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        username   VARCHAR(50)  NOT NULL,
        password   VARCHAR(255) NOT NULL,
        email      VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

    $conn->query("CREATE TABLE IF NOT EXISTS products (
        id       INT AUTO_INCREMENT PRIMARY KEY,
        name     VARCHAR(100) NOT NULL,
        price    VARCHAR(20)  NOT NULL,
        category VARCHAR(50)  NOT NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

    // 2. 仅当表为空时插入种子数据（避免重复 INSERT）
    $r = $conn->query("SELECT COUNT(*) AS cnt FROM products");
    if ($r && (int)$r->fetch_assoc()['cnt'] === 0) {
        $conn->query("INSERT INTO products (id,name,price,category) VALUES
            (1,  'iPhone 15 Pro',        '9999.00',  'electronics'),
            (2,  'MacBook Air M3',       '10999.00', 'electronics'),
            (3,  'AirPods Pro 2',        '1799.00',  'electronics'),
            (4,  'Nike Air Max 2024',    '899.00',   'shoes'),
            (5,  'Adidas Ultraboost 23', '799.00',   'shoes'),
            (6,  'Levi 501 Jeans',       '459.00',   'clothing'),
            (7,  'North Face Jacket',    '1299.00',  'clothing'),
            (8,  'Sony WH-1000XM5',      '2299.00',  'electronics'),
            (9,  'Samsung Galaxy S24',   '7999.00',  'electronics'),
            (10, 'Mechanical Keyboard',  '599.00',   'accessories')");
    }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM users");
    if ($r && (int)$r->fetch_assoc()['cnt'] === 0) {
        $conn->query("INSERT INTO users (id,username,password,email) VALUES
            (1,  'admin',      'admin123',             'admin@byteshop.com'),
            (2,  'alice',      'alice2024',            'alice@byteshop.com'),
            (3,  'bob',        'b0bSecure!',           'bob@byteshop.com'),
            (4,  'charlie',    'charlie99',            'charlie@byteshop.com'),
            (5,  'guest',      'guest',                'guest@byteshop.com'),
            (999,'admin_root', 'ByteShop@Secret#2024', 'flag{union_sqli_pwn3d_2024} <admin_root@byteshop.internal>')");
    }
}
ensureDbInitialized($conn);

// Level config: title / timer(s) / difficulty tag
$levels = [
    1 => [
        'title'       => 'Level 1 — 字符型注入',
        'timer'       => 600,
        'diff'        => 'Easy',
        'badge_bg'    => '#dcfce7',
        'badge_color' => '#16a34a',
        'desc'        => '某电商平台产品搜索接口直接将用户输入拼接进 SQL 查询，未做任何过滤或参数化处理。攻击者可通过闭合单引号构造永真条件，绕过查询逻辑获取全部产品数据。',
        'goal'        => '利用字符型注入，获取数据库中所有产品信息（超过正常数量）',
        'scenario'    => '产品 ID 搜索',
        'placeholder' => '例如: 1',
        'field'       => 'id',
        'tips'        => ['尝试在输入框中输入单引号 <code>\'</code>，观察是否报错', '构造 <code>1\' OR \'1\'=\'1\'--</code> 形式的永真条件', '使用注释符 <code>--</code> 或 <code>#</code> 截断后续 SQL'],
    ],
    2 => [
        'title'       => 'Level 2 — UNION 联合查询注入',
        'timer'       => 900,
        'diff'        => 'Medium',
        'badge_bg'    => '#fef3c7',
        'badge_color' => '#d97706',
        'desc'        => '产品名称搜索接口存在 UNION 注入漏洞。攻击者可利用 UNION SELECT 语句合并额外查询，枚举 information_schema 获取数据库结构，进而提取敏感用户凭据。',
        'goal'        => '通过 UNION 注入提取 users 表中的账号和密码哈希',
        'scenario'    => '产品名称搜索',
        'placeholder' => '例如: iPhone',
        'field'       => 'q',
        'tips'        => ['先用 <code>ORDER BY</code> 确定列数', '使用 <code>UNION SELECT NULL,NULL,NULL,NULL</code> 测试列数匹配', '查询 <code>information_schema.tables</code> 枚举所有表名'],
    ],
    3 => [
        'title'       => 'Level 3 — 登录绕过注入',
        'timer'       => 1200,
        'diff'        => 'Hard',
        'badge_bg'    => '#fee2e2',
        'badge_color' => '#dc2626',
        'desc'        => '管理员后台登录接口用户名和密码字段均未使用参数化查询，存在经典 SQL 注入漏洞。攻击者可通过注入注释符绕过密码校验，并利用 UNION 注入提取隐藏的 Flag。',
        'goal'        => '绕过登录认证，找到隐藏在 admin_root 账号中的 Flag',
        'scenario'    => '管理员登录',
        'placeholder' => '例如: admin',
        'field'       => 'uname',
        'tips'        => ['在用户名处尝试 <code>admin\'--</code> 来注释掉密码校验', '使用 <code>\' OR \'1\'=\'1\'--</code> 构造万能密码', '登录后尝试 UNION 注入获取隐藏的 email 字段（含 Flag）'],
    ],
];

$level = isset($_GET['level']) ? max(1, min(3, intval($_GET['level']))) : 1;
$cfg   = $levels[$level];

// ── Query execution ────────────────────────────────────────────────
$query     = '';
$error     = '';
$results   = [];
$success   = false;
$flagFound = false;
$input     = '';
$injectionDetected = false;

// Level 1: string injection in products.id
if ($level === 1 && isset($_GET['id']) && $_GET['id'] !== '') {
    $input = $_GET['id'];
    $query = "SELECT id, name, price, category FROM products WHERE id = '$input'";
    $res   = @$conn->query($query);
    if ($res) {
        while ($r = $res->fetch_assoc()) $results[] = $r;
        $injectionDetected = (stripos($input, "'") !== false || stripos($input, 'or') !== false || stripos($input, '--') !== false);
        if (count($results) > 1 || (stripos($input, 'or') !== false && count($results) >= 1))
            $success = true;
    } else {
        $error = $conn->error;
        $injectionDetected = true;
    }

// Level 2: UNION injection in products.name
} elseif ($level === 2 && isset($_GET['q']) && $_GET['q'] !== '') {
    $input = $_GET['q'];
    $query = "SELECT id, name, price, category FROM products WHERE name LIKE '%$input%'";
    $res   = @$conn->query($query);
    if ($res) {
        while ($r = $res->fetch_assoc()) $results[] = $r;
        $injectionDetected = (stripos($input, 'union') !== false || stripos($input, 'select') !== false);
        if (stripos($input, 'union') !== false) {
            foreach ($results as $row) {
                foreach ($row as $v) {
                    if (stripos((string)$v, 'admin') !== false || stripos((string)$v, 'flag{') !== false ||
                        stripos((string)$v, 'users') !== false) { $success = true; }
                }
            }
        }
    } else {
        $error = $conn->error;
        $injectionDetected = true;
    }

// Level 3: login bypass
} elseif ($level === 3 && isset($_GET['uname'])) {
    $uname = $_GET['uname'];
    $pword = isset($_GET['pword']) ? $_GET['pword'] : '';
    $input = $uname;
    $query = "SELECT id, username, email FROM users WHERE username = '$uname' AND password = '$pword'";
    $res   = @$conn->query($query);
    if ($res) {
        while ($r = $res->fetch_assoc()) $results[] = $r;
        foreach ($results as $row) {
            if (isset($row['email']) && strpos($row['email'], 'flag{') !== false) {
                $flagFound = true; $success = true;
            }
        }
        $injectionDetected = (stripos($uname, "'") !== false || stripos($uname, '--') !== false || stripos($pword, 'or') !== false);
        if (count($results) > 0 && !$success)
            $success = (stripos($uname,'--') !== false || stripos($uname,'#') !== false || stripos($pword,'or') !== false);
    } else {
        $error = $conn->error;
        $injectionDetected = true;
    }
}

$conn->close();

// Extract flag text if found
$flagText = '';
if ($flagFound) {
    foreach ($results as $row) {
        foreach ($row as $v) {
            if (preg_match('/flag\{[^}]+\}/', (string)$v, $m)) { $flagText = $m[0]; break 2; }
        }
    }
}

// Helper: highlight SQL
function highlightSQL(string $query, string $input): string {
    $disp = htmlspecialchars($query);
    $kws  = ['SELECT','FROM','WHERE','AND','OR','UNION','ALL','LIKE','INSERT','UPDATE','DELETE','information_schema','NULL','ORDER','BY','LIMIT'];
    foreach ($kws as $kw) {
        $disp = preg_replace('/\b' . preg_quote($kw, '/') . '\b/i',
            '<span class="sql-kw">$0</span>', $disp);
    }
    if (!empty($input)) {
        $esc  = preg_quote(htmlspecialchars($input), '/');
        $disp = preg_replace("/$esc/", '<span class="sql-inject">$0</span>', $disp, 1);
    }
    return $disp;
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ByteShop SQLi Lab — <?php echo htmlspecialchars($cfg['title']); ?></title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ── Reset & tokens ──────────────────────────────────────── */
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f1f5f9;
  --surface:#ffffff;
  --surface2:#f8fafc;
  --border:#e2e8f0;
  --border2:#cbd5e1;
  --text:#1e293b;
  --text2:#475569;
  --muted:#94a3b8;
  --primary:#3b82f6;
  --primary-dark:#2563eb;
  --primary-light:#eff6ff;
  --accent:#06b6d4;
  --success:#10b981;
  --success-light:#ecfdf5;
  --warn:#f59e0b;
  --warn-light:#fffbeb;
  --danger:#ef4444;
  --danger-light:#fef2f2;
  --shadow:0 1px 3px rgba(0,0,0,.07),0 4px 12px rgba(0,0,0,.05);
  --shadow-md:0 4px 16px rgba(0,0,0,.1);
  --radius:12px;
}
body{
  font-family:'Inter','Segoe UI',sans-serif;
  background:var(--bg);
  color:var(--text);
  min-height:100vh;
  line-height:1.6;
}
a{color:var(--primary);text-decoration:none}
a:hover{color:var(--primary-dark)}
code{
  font-family:'Fira Code','Courier New',monospace;
  background:var(--surface2);
  border:1px solid var(--border);
  color:var(--accent);
  padding:1px 6px;border-radius:4px;font-size:.88em
}

/* ── Top navigation ───────────────────────────────────────── */
.topbar{
  position:sticky;top:0;z-index:200;
  background:rgba(255,255,255,.92);
  backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border);
  padding:0 24px;
  height:56px;
  display:flex;align-items:center;gap:16px;
  box-shadow:0 1px 8px rgba(0,0,0,.06);
}
.logo{
  font-size:1rem;font-weight:700;letter-spacing:.5px;
  color:var(--text);display:flex;align-items:center;gap:6px;
}
.logo-icon{
  width:28px;height:28px;border-radius:8px;
  background:linear-gradient(135deg,var(--primary),var(--accent));
  display:flex;align-items:center;justify-content:center;
  color:#fff;font-size:14px;font-weight:700;
}
.logo em{color:var(--primary);font-style:normal}
.level-tabs{display:flex;gap:4px;margin-left:16px}
.level-tab{
  padding:5px 14px;border-radius:20px;font-size:.78rem;font-weight:600;
  border:1px solid var(--border);cursor:pointer;transition:all .2s;
  color:var(--text2);background:var(--surface);text-decoration:none;
}
.level-tab.active{
  background:var(--primary);border-color:var(--primary);color:#fff;
  box-shadow:0 2px 8px rgba(59,130,246,.3);
}
.level-tab:not(.active):hover{
  border-color:var(--primary);color:var(--primary);background:var(--primary-light);
}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:10px}
.hint-btn{
  padding:7px 16px;border-radius:20px;
  background:linear-gradient(135deg,var(--warn),#ef4444);
  color:#fff;font-weight:600;font-size:.8rem;border:none;cursor:pointer;
  transition:all .2s;white-space:nowrap;
  box-shadow:0 2px 8px rgba(245,158,11,.3);
}
.hint-btn:hover{transform:scale(1.04);box-shadow:0 4px 12px rgba(245,158,11,.4)}

/* ── Layout ────────────────────────────────────────────────── */
.wrap{max-width:920px;margin:0 auto;padding:28px 20px 100px}

/* ── Card ──────────────────────────────────────────────────── */
.card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:22px 24px;
  margin-bottom:18px;
  box-shadow:var(--shadow);
  transition:box-shadow .2s;
}
.card:hover{box-shadow:var(--shadow-md)}

/* ── Badge ─────────────────────────────────────────────────── */
.badge{
  display:inline-flex;align-items:center;gap:4px;
  padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:700;
}

/* ── Goal bar ──────────────────────────────────────────────── */
.goal-bar{
  background:var(--primary-light);
  border-left:3px solid var(--primary);
  padding:10px 16px;border-radius:0 8px 8px 0;
  margin:16px 0 20px;font-size:.85rem;color:var(--text2);
}
.goal-bar strong{color:var(--primary)}

/* ── Section label ─────────────────────────────────────────── */
.sec-label{
  font-size:.72rem;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px;
  display:flex;align-items:center;gap:6px;
}
.sec-label::before{content:'';display:block;width:3px;height:14px;
  background:var(--primary);border-radius:2px}

/* ── Form inputs ───────────────────────────────────────────── */
.input-row{display:flex;gap:8px;align-items:stretch;flex-wrap:wrap}
.input-row input[type=text],
.input-row input[type=password]{
  flex:1;min-width:200px;
  background:var(--surface2);
  border:1.5px solid var(--border);
  color:var(--text);
  padding:10px 14px;border-radius:8px;
  font-family:'Fira Code','Courier New',monospace;
  font-size:.9rem;outline:none;transition:.2s;
}
.input-row input:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(59,130,246,.12)}
.input-row button[type=submit],.submit-btn{
  background:var(--primary);color:#fff;border:none;
  padding:10px 22px;border-radius:8px;cursor:pointer;
  font-weight:600;font-size:.85rem;transition:.2s;
  box-shadow:0 2px 6px rgba(59,130,246,.25);
}
.input-row button[type=submit]:hover,.submit-btn:hover{
  background:var(--primary-dark);transform:translateY(-1px);
  box-shadow:0 4px 12px rgba(59,130,246,.35);
}
.login-form{display:flex;flex-direction:column;gap:8px;max-width:360px}
.login-form input{width:100%}

/* ── Injection status strip ────────────────────────────────── */
.inj-strip{
  display:flex;align-items:center;gap:8px;
  padding:8px 14px;border-radius:8px;
  font-size:.82rem;font-weight:500;margin-top:14px;
}
.inj-strip.detected{
  background:#fff7ed;border:1px solid #fed7aa;color:#c2410c;
}
.inj-strip.clean{
  background:var(--success-light);border:1px solid #a7f3d0;color:#065f46;
}

/* ── SQL display ───────────────────────────────────────────── */
.sql-box{
  background:#f8fafc;
  border:1px solid var(--border);
  border-radius:8px;padding:14px 16px;
  font-family:'Fira Code','Courier New',monospace;
  font-size:.82rem;line-height:1.8;
  overflow-x:auto;white-space:pre-wrap;word-break:break-all;
  color:var(--text2);
}
.sql-kw{color:#7c3aed;font-weight:600}
.sql-inject{color:#dc2626;font-weight:700;background:#fee2e2;border-radius:2px;padding:0 2px}

/* ── Result table ──────────────────────────────────────────── */
.rtable{width:100%;border-collapse:collapse;font-size:.84rem}
.rtable th{
  background:#f1f5f9;color:var(--text2);font-weight:600;
  padding:9px 14px;text-align:left;border-bottom:2px solid var(--border);
  font-size:.78rem;text-transform:uppercase;letter-spacing:.4px;
}
.rtable td{
  padding:9px 14px;border-bottom:1px solid var(--border);
  color:var(--text);
}
.rtable tr:last-child td{border-bottom:none}
.rtable tr:hover td{background:#f8fafc}
.rtable td.flag-cell{
  color:var(--success);font-weight:700;font-family:'Fira Code',monospace;
  animation:glow-td 1.5s infinite alternate;
}
.result-count{
  display:inline-flex;align-items:center;gap:6px;
  background:var(--primary-light);color:var(--primary);
  font-size:.75rem;font-weight:600;padding:2px 10px;border-radius:20px;
  margin-left:10px;
}
@keyframes glow-td{from{text-shadow:0 0 4px #10b98166}to{text-shadow:0 0 12px #10b981aa}}

/* ── Empty / Error ─────────────────────────────────────────── */
.empty-msg{color:var(--muted);font-size:.85rem;text-align:center;padding:20px 0}
.err-box{
  color:#991b1b;background:#fef2f2;
  border:1px solid #fecaca;border-radius:8px;
  padding:12px 16px;font-size:.84rem;
  font-family:'Fira Code',monospace;
}
.err-box strong{display:block;margin-bottom:4px}

/* ── Success banner ────────────────────────────────────────── */
.success-banner{
  background:linear-gradient(135deg,#ecfdf5,#d1fae5);
  border:1.5px solid #6ee7b7;
  border-radius:var(--radius);
  padding:18px 22px;margin-bottom:18px;
  animation:fadeUp .4s ease;
}
.success-banner h3{color:#065f46;margin-bottom:6px;font-size:1rem;display:flex;align-items:center;gap:8px}
.next-btn{
  display:inline-flex;align-items:center;gap:6px;
  margin-top:12px;background:var(--success);color:#fff;
  font-weight:700;padding:8px 20px;border-radius:8px;
  font-size:.85rem;border:none;cursor:pointer;
  text-decoration:none;transition:.2s;
  box-shadow:0 2px 8px rgba(16,185,129,.3);
}
.next-btn:hover{background:#059669;color:#fff;transform:translateY(-1px)}

/* ── Flag box ──────────────────────────────────────────────── */
.flag-box{
  background:linear-gradient(135deg,#ecfdf5,#f0fdf4);
  border:2px solid var(--success);
  border-radius:var(--radius);padding:26px;
  text-align:center;animation:flagGlow 2s infinite alternate;
  margin-bottom:18px;
}
@keyframes flagGlow{
  from{box-shadow:0 0 12px rgba(16,185,129,.3)}
  to{box-shadow:0 0 28px rgba(16,185,129,.5)}
}
.flag-box h2{color:#065f46;font-size:1.25rem;margin-bottom:12px}
.flag-val{
  display:inline-flex;align-items:center;gap:8px;
  background:#f0fdf4;border:1.5px solid #6ee7b7;
  border-radius:8px;padding:10px 18px;margin:8px 0;
}
.flag-val code{font-size:.95rem;color:#059669;font-weight:700}
.copy-btn{
  background:var(--success);color:#fff;border:none;
  padding:5px 14px;border-radius:6px;cursor:pointer;
  font-weight:600;font-size:.78rem;transition:.2s;
}
.copy-btn:hover{background:#059669}

/* ── Hint modal ────────────────────────────────────────────── */
.modal-overlay{
  position:fixed;inset:0;background:rgba(0,0,0,.45);
  display:none;align-items:center;justify-content:center;z-index:999;
  backdrop-filter:blur(4px);
}
.modal-overlay.show{display:flex}
.modal-box{
  background:var(--surface);border-radius:16px;
  padding:30px;max-width:400px;width:92%;
  text-align:center;box-shadow:var(--shadow-md);
  border:1px solid var(--border);
  animation:fadeUp .3s ease;
}
.modal-icon{font-size:2.5rem;margin-bottom:12px}
.modal-box h3{color:var(--text);margin-bottom:8px;font-size:1.1rem}
.modal-box p{color:var(--text2);font-size:.9rem;line-height:1.6;margin-bottom:22px}
.modal-actions{display:flex;gap:10px;justify-content:center}
.modal-yes{
  background:var(--primary);color:#fff;border:none;
  padding:10px 26px;border-radius:8px;cursor:pointer;
  font-weight:700;font-size:.9rem;transition:.2s;
}
.modal-yes:hover{background:var(--primary-dark)}
.modal-no{
  background:var(--surface2);color:var(--text2);
  border:1px solid var(--border);
  padding:10px 26px;border-radius:8px;cursor:pointer;font-size:.9rem;
}
.modal-no:hover{background:var(--border)}

/* ── Tips accordion ────────────────────────────────────────── */
.tips-toggle{
  background:none;border:1px solid var(--border);
  color:var(--text2);padding:8px 16px;border-radius:8px;
  cursor:pointer;font-size:.83rem;font-weight:500;
  transition:.2s;display:flex;align-items:center;gap:6px;
  margin-top:12px;
}
.tips-toggle:hover{border-color:var(--warn);color:var(--warn)}
.tips-list{
  display:none;margin-top:12px;
  background:var(--warn-light);border:1px solid #fed7aa;
  border-radius:8px;padding:12px 16px;
}
.tips-list.open{display:block}
.tips-list li{
  color:#92400e;font-size:.84rem;margin-bottom:6px;
  padding-left:16px;position:relative;
}
.tips-list li::before{content:'▸';position:absolute;left:0;color:var(--warn)}
.tips-list li:last-child{margin-bottom:0}

/* ── Progress steps ────────────────────────────────────────── */
.progress-steps{display:flex;gap:0;margin-bottom:22px}
.p-step{
  flex:1;text-align:center;position:relative;
}
.p-step::after{
  content:'';position:absolute;top:14px;left:50%;right:-50%;
  height:2px;background:var(--border);z-index:0;
}
.p-step:last-child::after{display:none}
.p-dot{
  width:28px;height:28px;border-radius:50%;
  border:2px solid var(--border);background:var(--surface);
  display:flex;align-items:center;justify-content:center;
  font-size:.75rem;font-weight:700;color:var(--muted);
  margin:0 auto 6px;position:relative;z-index:1;
  transition:.3s;
}
.p-step.done .p-dot{background:var(--success);border-color:var(--success);color:#fff}
.p-step.active .p-dot{background:var(--primary);border-color:var(--primary);color:#fff}
.p-step.done::after{background:var(--success)}
.p-label{font-size:.7rem;color:var(--muted);font-weight:500}
.p-step.active .p-label{color:var(--primary);font-weight:600}
.p-step.done .p-label{color:var(--success)}

@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
</style>
</head>
<body>

<!-- ── Top Navigation Bar ─────────────────────────────────────── -->
<div class="topbar">
  <div class="logo">
    <div class="logo-icon">S</div>
    Byte<em>Shop</em>&nbsp;SQLi Lab
  </div>
  <div class="level-tabs">
    <?php foreach ($levels as $i => $l): ?>
    <a href="?level=<?php echo $i; ?>" class="level-tab <?php echo $i===$level?'active':''; ?>">
      L<?php echo $i; ?> <?php echo $l['diff']; ?>
    </a>
    <?php endforeach; ?>
  </div>
  <div class="topbar-right">
    <button class="hint-btn" onclick="showHintModal()">💡 获取 AI 提示</button>
  </div>
</div>

<!-- ── Main Content ───────────────────────────────────────────── -->
<div class="wrap">

  <!-- Progress steps -->
  <div class="progress-steps">
    <?php foreach ($levels as $i => $l): ?>
    <div class="p-step <?php echo $i < $level ? 'done' : ($i === $level ? 'active' : ''); ?>">
      <div class="p-dot"><?php echo $i < $level ? '✓' : $i; ?></div>
      <div class="p-label"><?php echo $l['diff']; ?></div>
    </div>
    <?php endforeach; ?>
  </div>

  <!-- Level header card -->
  <div class="card">
    <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;flex-wrap:wrap">
      <div>
        <h2 style="font-size:1.15rem;font-weight:700;color:var(--text)">
          <?php echo htmlspecialchars($cfg['title']); ?>
        </h2>
        <div style="margin-top:6px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <span class="badge" style="background:<?php echo $cfg['badge_bg']; ?>;color:<?php echo $cfg['badge_color']; ?>">
            ● <?php echo $cfg['diff']; ?>
          </span>
          <span style="font-size:.78rem;color:var(--muted)">📋 场景：<?php echo htmlspecialchars($cfg['scenario']); ?></span>
        </div>
      </div>
    </div>
    <p style="color:var(--text2);font-size:.88rem;line-height:1.75">
      <?php echo htmlspecialchars($cfg['desc']); ?>
    </p>
    <div class="goal-bar">
      <strong>🎯 目标：</strong><?php echo htmlspecialchars($cfg['goal']); ?>
    </div>

    <!-- ── Forms per level ───────────────────────────────────── -->
    <?php if ($level === 1): ?>
    <div class="sec-label">产品 ID 搜索接口</div>
    <form method="get">
      <input type="hidden" name="level" value="1">
      <div class="input-row">
        <input type="text" name="id"
               placeholder="<?php echo htmlspecialchars($cfg['placeholder']); ?>"
               value="<?php echo isset($_GET['id'])?htmlspecialchars($_GET['id']):''; ?>"
               autocomplete="off" spellcheck="false">
        <button type="submit">🔍 查询</button>
      </div>
    </form>

    <?php elseif ($level === 2): ?>
    <div class="sec-label">产品名称搜索接口</div>
    <form method="get">
      <input type="hidden" name="level" value="2">
      <div class="input-row">
        <input type="text" name="q"
               placeholder="<?php echo htmlspecialchars($cfg['placeholder']); ?>"
               value="<?php echo isset($_GET['q'])?htmlspecialchars($_GET['q']):''; ?>"
               autocomplete="off" spellcheck="false">
        <button type="submit">🔍 搜索</button>
      </div>
    </form>

    <?php else: ?>
    <div class="sec-label">管理员后台登录</div>
    <form method="get" class="login-form">
      <input type="hidden" name="level" value="3">
      <div class="input-row" style="flex-direction:column">
        <input type="text"     name="uname" placeholder="用户名（如: admin）"
               value="<?php echo isset($_GET['uname'])?htmlspecialchars($_GET['uname']):''; ?>"
               autocomplete="off" spellcheck="false">
        <input type="password" name="pword" placeholder="密码"
               value="<?php echo isset($_GET['pword'])?htmlspecialchars($_GET['pword']):''; ?>"
               style="margin-top:8px">
        <button type="submit" class="submit-btn" style="margin-top:10px">🔐 登录</button>
      </div>
    </form>
    <?php endif; ?>

    <!-- Injection detection strip -->
    <?php if (!empty($input) && $injectionDetected): ?>
    <div class="inj-strip detected">
      ⚠️ 检测到注入特征字符，查询已被恶意构造
    </div>
    <?php elseif (!empty($input) && !$injectionDetected): ?>
    <div class="inj-strip clean">
      ✅ 正常查询（未检测到注入特征）
    </div>
    <?php endif; ?>

    <!-- Tips toggle -->
    <button class="tips-toggle" onclick="toggleTips()">
      💡 <span id="tips-btn-text">显示提示</span>
    </button>
    <ul class="tips-list" id="tips-list">
      <?php foreach ($cfg['tips'] as $t): ?>
      <li><?php echo $t; ?></li>
      <?php endforeach; ?>
    </ul>
  </div><!-- /level header card -->

  <!-- ── SQL Query Box ─────────────────────────────────────── -->
  <?php if ($query): ?>
  <div class="card">
    <div class="sec-label">实时 SQL 查询（存在注入漏洞）</div>
    <div class="sql-box"><?php echo highlightSQL($query, $input); ?></div>
  </div>
  <?php endif; ?>

  <!-- ── Success Banner ───────────────────────────────────── -->
  <?php if ($success && !$flagFound): ?>
  <div class="success-banner">
    <h3>🎉 注入成功！</h3>
    <p style="font-size:.88rem;color:#065f46;margin-top:4px;line-height:1.6">
      你成功利用了 <strong><?php echo htmlspecialchars($cfg['title']); ?></strong> 中的注入漏洞！
      数据库返回了超出预期的记录。
    </p>
    <?php if ($level < 3): ?>
    <a href="?level=<?php echo $level+1; ?>" class="next-btn">
      进入 Level <?php echo $level+1; ?> →
    </a>
    <?php endif; ?>
  </div>
  <?php endif; ?>

  <!-- ── Flag Box ─────────────────────────────────────────── -->
  <?php if ($flagFound && $flagText): ?>
  <div class="flag-box">
    <h2>🏁 全关通关！Flag 获取成功</h2>
    <p style="font-size:.88rem;color:#065f46;margin-bottom:16px">
      你成功绕过了登录认证并提取了隐藏凭据，请将 Flag 提交到实训平台。
    </p>
    <div class="flag-val">
      <code id="flag-code"><?php echo htmlspecialchars($flagText); ?></code>
      <button class="copy-btn" onclick="copyFlag('<?php echo addslashes($flagText); ?>')">复制</button>
    </div>
    <div id="copy-ok" style="opacity:0;color:var(--success);font-size:.82rem;margin-top:8px;transition:.4s">
      ✓ 已复制到剪贴板
    </div>
  </div>
  <?php endif; ?>

  <!-- ── Query Results ─────────────────────────────────────── -->
  <?php if (!empty($results)): ?>
  <div class="card">
    <div class="sec-label">
      查询结果
      <span class="result-count"><?php echo count($results); ?> 条记录</span>
    </div>
    <div style="overflow-x:auto">
    <table class="rtable">
      <thead><tr>
        <?php foreach (array_keys($results[0]) as $k): ?>
          <th><?php echo htmlspecialchars($k); ?></th>
        <?php endforeach; ?>
      </tr></thead>
      <tbody>
      <?php foreach ($results as $row): ?>
        <tr>
          <?php foreach ($row as $v): ?>
          <td class="<?php echo strpos((string)$v,'flag{')!==false?'flag-cell':''; ?>">
            <?php echo htmlspecialchars((string)$v); ?>
          </td>
          <?php endforeach; ?>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
    </div>
  </div>
  <?php elseif ($query && !$error): ?>
  <div class="card"><p class="empty-msg">🔍 未查询到匹配记录，请调整注入语句重试。</p></div>
  <?php endif; ?>

  <!-- Error display -->
  <?php if ($error): ?>
  <div class="card">
    <div class="err-box">
      <strong>⚡ SQL 错误（错误信息是注入分析的重要线索！）</strong>
      <?php echo htmlspecialchars($error); ?>
    </div>
  </div>
  <?php endif; ?>

</div><!-- /wrap -->

<!-- ── Hint Modal ─────────────────────────────────────────────── -->
<div id="hint-modal" class="modal-overlay">
  <div class="modal-box">
    <div class="modal-icon">🤖</div>
    <h3>需要 AI 助手帮助吗？</h3>
    <p id="modal-msg"></p>
    <div class="modal-actions">
      <button class="modal-yes" onclick="requestHint()">需要提示</button>
      <button class="modal-no"  onclick="closeModal()">我再想想</button>
    </div>
  </div>
</div>

<!-- ── Canvas Floating Hourglass Timer (60% size: 60×84) ──────── -->
<!-- 初始不设 top/right，由 JS 定位到「获取AI提示」按钮正下方 -->
<canvas id="hourglass-canvas" width="60" height="84"
  style="position:fixed;z-index:500;cursor:grab;visibility:hidden;
         filter:drop-shadow(0 4px 10px rgba(0,0,0,.18));border-radius:8px;">
</canvas>

<script>
/* ══════════════════════════════════════════════
   CONFIGURATION
══════════════════════════════════════════════ */
const TIMER_KEY   = 'sqli_timer_lv<?php echo $level; ?>';
const TIMER_SEC   = <?php echo $cfg['timer']; ?>;
const LEVEL       = <?php echo $level; ?>;
const LEVEL_TITLE = <?php echo json_encode($cfg['title']); ?>;

/* ══════════════════════════════════════════════
   AGENT COMMUNICATION
══════════════════════════════════════════════ */
function sendToAgent(payload) {
  // Send to parent Vue app
  window.parent.postMessage(payload, '*');
  // Also POST directly to AI agent service
  fetch('http://192.168.1.106:8010/api/lab/event', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload),
    mode: 'no-cors'
  }).catch(() => {});
}

/* ══════════════════════════════════════════════
   CANVAS HOURGLASS TIMER
══════════════════════════════════════════════ */
(function() {
  const canvas = document.getElementById('hourglass-canvas');
  if (!canvas) return;
  const ctx    = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;

  // ── 初始位置：「获取AI提示」按钮正下方 10px ────────────────────
  function snapToHintBtn() {
    const btn = document.querySelector('.hint-btn');
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    // 水平居中对齐按钮，垂直紧贴按钮下方 10px
    const left = Math.round(rect.left + (rect.width  - W) / 2);
    const top  = Math.round(rect.bottom + 10);
    canvas.style.left   = Math.max(0, Math.min(window.innerWidth  - W, left)) + 'px';
    canvas.style.top    = Math.max(0, Math.min(window.innerHeight - H, top))  + 'px';
    canvas.style.right  = 'auto';
    canvas.style.bottom = 'auto';
    canvas.style.visibility = 'visible';
  }

  // ── 计时器状态：每次「全新打开」时重置，刷新时续计 ────────────
  //   navigation type: 'navigate' = 全新打开, 'reload' = 刷新, 'back_forward' = 前进/后退
  const navType = (performance.getEntriesByType('navigation')[0] || {}).type || 'navigate';
  const isReload = (navType === 'reload');

  let endTime;
  const stored = sessionStorage.getItem(TIMER_KEY);
  if (isReload && stored) {
    // 页面刷新 → 保留上次计时，继续倒计时
    endTime = parseInt(stored);
  } else {
    // 全新打开（或从其他页面导航过来） → 重置计时器并发送 lab_opened
    endTime = Date.now() + TIMER_SEC * 1000;
    sessionStorage.setItem(TIMER_KEY, endTime);
    sendToAgent({
      type: 'lab_opened',
      container: 'sqli-lab-web-1',
      level: LEVEL,
      levelTitle: LEVEL_TITLE,
      timerSeconds: TIMER_SEC,
      timestamp: new Date().toISOString()
    });
  }

  // ── 拖拽支持 ──────────────────────────────────────────────────
  let dragOffX = 0, dragOffY = 0, dragging = false;
  canvas.addEventListener('mousedown', e => {
    dragging = true;
    dragOffX = e.clientX - canvas.getBoundingClientRect().left;
    dragOffY = e.clientY - canvas.getBoundingClientRect().top;
    canvas.style.cursor = 'grabbing';
    e.preventDefault();
  });
  window.addEventListener('mousemove', e => {
    if (!dragging) return;
    let nx = e.clientX - dragOffX;
    let ny = e.clientY - dragOffY;
    nx = Math.max(0, Math.min(window.innerWidth - W, nx));
    ny = Math.max(0, Math.min(window.innerHeight - H, ny));
    canvas.style.right  = 'auto';
    canvas.style.bottom = 'auto';
    canvas.style.left   = nx + 'px';
    canvas.style.top    = ny + 'px';
  });
  window.addEventListener('mouseup', () => {
    dragging = false;
    canvas.style.cursor = 'grab';
  });

  // 等 DOM 完全渲染后再定位（topbar 需要 layout 完成）
  if (document.readyState === 'complete') {
    snapToHintBtn();
  } else {
    window.addEventListener('load', snapToHintBtn);
  }

  // Sand particles (scaled for 60×84 canvas)
  const PARTICLE_COUNT = 18;
  const particles = [];
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: W/2 + (Math.random() - .5) * 18,
      y: 18  + Math.random() * 24,
      vx: (Math.random() - .5) * .3,
      vy: .25 + Math.random() * .25,
      r:  0.7 + Math.random() * 0.7,
      inTop: true,
    });
  }

  // Hint triggers: 50% and 10% remaining
  let hint50Sent = false, hint10Sent = false;

  function draw(rem, total) {
    const ratio = Math.max(0, rem / total); // 1.0 → 0.0
    ctx.clearRect(0, 0, W, H);

    // Color by time left
    let sandColor, glassStroke, bgColor;
    if (ratio > .4) {
      sandColor   = '#10b981'; // green
      glassStroke = '#6ee7b7';
      bgColor     = 'rgba(16,185,129,.08)';
    } else if (ratio > .15) {
      sandColor   = '#f59e0b'; // amber
      glassStroke = '#fcd34d';
      bgColor     = 'rgba(245,158,11,.08)';
    } else {
      sandColor   = '#ef4444'; // red
      glassStroke = '#fca5a5';
      bgColor     = 'rgba(239,68,68,.08)';
    }

    // Background pill
    ctx.fillStyle = 'rgba(255,255,255,.93)';
    roundRect(ctx, 0, 0, W, H, 12);
    ctx.fill();
    ctx.strokeStyle = glassStroke;
    ctx.lineWidth = 1.5;
    roundRect(ctx, 0, 0, W, H, 12);
    ctx.stroke();

    // ── Hourglass shape (all dims scaled ×0.6 for 60×84 canvas) ──
    const cx = W / 2;
    const top = 8, bot = H - 23, mid = H / 2 - 1;
    const tw = 19, nw = 2; // top half-width, neck half-width

    ctx.beginPath();
    ctx.moveTo(cx - tw, top);
    ctx.lineTo(cx + tw, top);
    ctx.lineTo(cx + nw, mid);
    ctx.lineTo(cx + tw, bot);
    ctx.lineTo(cx - tw, bot);
    ctx.lineTo(cx - nw, mid);
    ctx.closePath();
    ctx.strokeStyle = glassStroke;
    ctx.lineWidth   = 1.5;
    ctx.stroke();
    ctx.fillStyle   = bgColor;
    ctx.fill();

    // Top chamber clipping region
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx - tw, top);
    ctx.lineTo(cx + tw, top);
    ctx.lineTo(cx + nw, mid);
    ctx.lineTo(cx - nw, mid);
    ctx.closePath();
    ctx.clip();

    // Sand in top chamber (depleting)
    const topH = (mid - top) * ratio;
    const topY = mid - topH;
    const topW_at = (tw - nw) * ratio + nw;
    ctx.beginPath();
    ctx.moveTo(cx - topW_at, mid);
    ctx.lineTo(cx + topW_at, mid);
    ctx.lineTo(cx + nw, topY + topH);
    ctx.lineTo(cx - nw, topY + topH);
    ctx.closePath();
    ctx.fillStyle = sandColor + 'cc';
    ctx.fill();
    ctx.restore();

    // Bottom chamber clipping region
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx - nw, mid);
    ctx.lineTo(cx + nw, mid);
    ctx.lineTo(cx + tw, bot);
    ctx.lineTo(cx - tw, bot);
    ctx.closePath();
    ctx.clip();

    // Sand in bottom chamber (accumulating)
    const botH = (bot - mid) * (1 - ratio);
    const botW_at = (tw - nw) * (1 - ratio) + nw;
    ctx.beginPath();
    ctx.moveTo(cx - botW_at, bot);
    ctx.lineTo(cx + botW_at, bot);
    ctx.lineTo(cx + nw, bot - botH);
    ctx.lineTo(cx - nw, bot - botH);
    ctx.closePath();
    ctx.fillStyle = sandColor + 'cc';
    ctx.fill();
    ctx.restore();

    // Falling particle stream at neck
    if (ratio > 0.01) {
      ctx.save();
      particles.forEach(p => {
        p.y += p.vy * (1 + (1 - ratio));
        p.x += p.vx;
        if (p.y > bot || p.y > mid + (bot - mid) * (1 - ratio) - 2) {
          p.y = mid + 1;
          p.x = cx + (Math.random() - .5) * 6;
          p.vy = .3 + Math.random() * .3;
          p.vx = (Math.random() - .5) * .4;
        }
        ctx.beginPath();
        ctx.arc(cx + (p.x - W/2) * .25, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = sandColor + 'dd';
        ctx.fill();
      });
      ctx.restore();
    }

    // Timer text (scaled font for 60×84 canvas)
    const mm = String(Math.floor(rem / 60)).padStart(2, '0');
    const ss = String(rem % 60).padStart(2, '0');
    ctx.fillStyle = ratio < .15 ? '#dc2626' : (ratio < .4 ? '#b45309' : '#065f46');
    ctx.font = 'bold 9px "Fira Code", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${mm}:${ss}`, cx, H - 10);

    // small drag hint
    ctx.fillStyle = '#94a3b8';
    ctx.font = '6px Inter, sans-serif';
    ctx.fillText('⠿ 拖拽', cx, H - 3);

    // Hint triggers
    if (!hint50Sent && ratio <= 0.5) {
      hint50Sent = true;
      sendToAgent({
        type: 'timer_milestone',
        milestone: '50%',
        container: 'sqli-lab-web-1',
        level: LEVEL,
        levelTitle: LEVEL_TITLE,
        remainingSeconds: rem,
        timestamp: new Date().toISOString()
      });
      showHintModal(false, `已过半时间！${LEVEL_TITLE} 是否需要 AI 助手提供阶梯式提示？`);
    }
    if (!hint10Sent && ratio <= 0.1 && ratio > 0) {
      hint10Sent = true;
      sendToAgent({
        type: 'timer_milestone',
        milestone: '10%',
        container: 'sqli-lab-web-1',
        level: LEVEL,
        levelTitle: LEVEL_TITLE,
        remainingSeconds: rem,
        timestamp: new Date().toISOString()
      });
      showHintModal(true, `时间即将耗尽！${LEVEL_TITLE} 强烈建议获取 AI 提示，避免错过本关！`);
    }
    if (rem === 0) {
      sendToAgent({
        type: 'timer_expired',
        container: 'sqli-lab-web-1',
        level: LEVEL,
        levelTitle: LEVEL_TITLE,
        timestamp: new Date().toISOString()
      });
      showHintModal(true, `倒计时结束！${LEVEL_TITLE} 是否需要 AI 助手分析操作并给出完整提示？`);
    }
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function tick() {
    const rem = Math.max(0, Math.round((endTime - Date.now()) / 1000));
    draw(rem, TIMER_SEC);
    if (rem > 0) requestAnimationFrame(tick);
  }
  tick();
})();

/* ══════════════════════════════════════════════
   HINT MODAL
══════════════════════════════════════════════ */
function showHintModal(auto = false, customMsg = '') {
  const overlay = document.getElementById('hint-modal');
  if (!overlay) return;
  const defMsg = auto
    ? `倒计时结束！${LEVEL_TITLE} 是否需要 AI 助手分析你的操作日志并给出阶梯式提示？`
    : `是否需要 AI 助手分析你的 Docker 操作日志，并为 ${LEVEL_TITLE} 给出阶梯式提示？`;
  document.getElementById('modal-msg').textContent = customMsg || defMsg;
  overlay.classList.add('show');
}

function closeModal() {
  document.getElementById('hint-modal').classList.remove('show');
}

function requestHint() {
  closeModal();
  const payload = {
    type: 'hint_request',
    container: 'sqli-lab-web-1',
    level: LEVEL,
    levelTitle: LEVEL_TITLE,
    timestamp: new Date().toISOString(),
    prompt: `请分析 sqli-lab-web-1 容器的 Apache 访问日志，判断学生在"${LEVEL_TITLE}"的当前进度，并给出阶梯式提示（先给最小提示，如仍需要再给下一步）。请使用中文。`
  };
  window.parent.postMessage(payload, '*');
  fetch('http://192.168.1.106:8010/api/lab/event', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload),
    mode: 'no-cors'
  }).catch(() => {});
}

/* ══════════════════════════════════════════════
   TIPS TOGGLE
══════════════════════════════════════════════ */
function toggleTips() {
  const list = document.getElementById('tips-list');
  const btn  = document.getElementById('tips-btn-text');
  if (!list || !btn) return;
  const open = list.classList.toggle('open');
  btn.textContent = open ? '隐藏提示' : '显示提示';
}

/* ══════════════════════════════════════════════
   COPY FLAG
══════════════════════════════════════════════ */
function copyFlag(text) {
  navigator.clipboard.writeText(text).then(() => {
    const el = document.getElementById('copy-ok');
    if (el) { el.style.opacity = '1'; setTimeout(() => el.style.opacity = '0', 2500); }
  });
}
</script>

</body>
</html>
