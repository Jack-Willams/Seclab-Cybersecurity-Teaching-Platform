<?php
// ════════════════════════════════════════════════════════════════
//  Protocol Analysis Lab – 网络协议分析训练靶场
//  Three levels: TCP/IP Analysis / HTTP Analysis / Security Analysis
// ════════════════════════════════════════════════════════════════
header('Content-Type: text/html; charset=utf-8');

$host   = "db";
$dbuser = "root";
$dbpass = "123456";
$dbname = "protocol_lab";

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

// ── 自动初始化数据库（保底措施）──
function ensureDbInitialized(mysqli $conn): void {
    $conn->query("CREATE TABLE IF NOT EXISTS packets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        timestamp VARCHAR(50) NOT NULL,
        source_ip VARCHAR(50) NOT NULL,
        destination_ip VARCHAR(50) NOT NULL,
        protocol VARCHAR(20) NOT NULL,
        source_port VARCHAR(10),
        destination_port VARCHAR(10),
        length INT NOT NULL,
        flags VARCHAR(20),
        payload TEXT,
        info VARCHAR(255)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

    $conn->query("CREATE TABLE IF NOT EXISTS http_requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        method VARCHAR(10) NOT NULL,
        path VARCHAR(255) NOT NULL,
        protocol VARCHAR(20) NOT NULL,
        host VARCHAR(100),
        user_agent VARCHAR(255),
        referer VARCHAR(255),
        cookie TEXT,
        body TEXT,
        status_code INT,
        response_headers TEXT,
        response_body TEXT,
        captured_at VARCHAR(50) NOT NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

    $conn->query("CREATE TABLE IF NOT EXISTS security_events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        event_type VARCHAR(50) NOT NULL,
        severity VARCHAR(20) NOT NULL,
        source_ip VARCHAR(50),
        destination_ip VARCHAR(50),
        description TEXT,
        timestamp VARCHAR(50) NOT NULL,
        flag VARCHAR(100)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

    $conn->query("CREATE TABLE IF NOT EXISTS network_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(50) NOT NULL,
        source_ip VARCHAR(50) NOT NULL,
        destination_ip VARCHAR(50) NOT NULL,
        protocol VARCHAR(20) NOT NULL,
        source_port VARCHAR(10),
        destination_port VARCHAR(10),
        start_time VARCHAR(50) NOT NULL,
        end_time VARCHAR(50),
        duration VARCHAR(20),
        packet_count INT,
        byte_count INT,
        status VARCHAR(20) NOT NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

    $conn->query("CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL,
        password VARCHAR(255) NOT NULL,
        email VARCHAR(100),
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM packets");
    if ($r && (int)$r->fetch_assoc()['cnt'] === 0) {
        $conn->query("INSERT INTO packets (id,timestamp,source_ip,destination_ip,protocol,source_port,destination_port,length,flags,payload,info) VALUES
            (1,'2024-01-15 10:30:00.123456','192.168.1.100','192.168.1.200','TCP','49152','80',60,'SYN','','TCP SYN'),
            (2,'2024-01-15 10:30:00.123567','192.168.1.200','192.168.1.100','TCP','80','49152',60,'SYN,ACK','','TCP SYN-ACK'),
            (3,'2024-01-15 10:30:00.123678','192.168.1.100','192.168.1.200','TCP','49152','80',52,'ACK','','TCP ACK'),
            (4,'2024-01-15 10:30:00.124123','192.168.1.100','192.168.1.200','HTTP','49152','80',256,'','GET /api/users HTTP/1.1','HTTP GET'),
            (5,'2024-01-15 10:30:00.124567','192.168.1.200','192.168.1.100','HTTP','80','49152',512,'','HTTP/1.1 200 OK','HTTP Response'),
            (6,'2024-01-15 10:30:01.000000','10.0.0.5','10.0.0.10','UDP','53','53',72,'','DNS Query','DNS Query'),
            (7,'2024-01-15 10:30:01.000123','10.0.0.10','10.0.0.5','UDP','53','53',102,'','DNS Response','DNS Response'),
            (8,'2024-01-15 10:30:05.555555','172.16.0.1','172.16.0.255','ARP','','',42,'','ARP Request','ARP Request'),
            (9,'2024-01-15 10:30:10.999999','192.168.1.100','192.168.1.200','TCP','49152','80',52,'FIN,ACK','','TCP FIN-ACK'),
            (10,'2024-01-15 10:30:11.000000','192.168.1.200','192.168.1.100','TCP','80','49152',52,'ACK','','TCP ACK')");
    }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM http_requests");
    if ($r && (int)$r->fetch_assoc()['cnt'] === 0) {
        $conn->query("INSERT INTO http_requests (id,method,path,protocol,host,user_agent,referer,cookie,body,status_code,response_headers,response_body,captured_at) VALUES
            (1,'GET','/','HTTP/1.1','localhost','Mozilla/5.0',NULL,'session=xyz789',NULL,200,'Content-Type: text/html','<html>Welcome</html>','2024-01-15 10:00:00'),
            (2,'POST','/login','HTTP/1.1','localhost','Mozilla/5.0','http://localhost/',NULL,'username=admin&password=secret123',200,'Set-Cookie: session=abc123','{\"status\":\"success\"}','2024-01-15 10:00:05'),
            (3,'GET','/api/secret','HTTP/1.1','localhost','Mozilla/5.0',NULL,'session=flag{http_analysis_master_2024}',NULL,200,'Content-Type: application/json','{\"secret\":\"flag{http_analysis_master_2024}\"}','2024-01-15 10:00:10'),
            (4,'GET','/robots.txt','HTTP/1.1','localhost','curl/7.81.0',NULL,NULL,NULL,200,'Content-Type: text/plain','Disallow: /admin\\nDisallow: /secret','2024-01-15 10:00:15'),
            (5,'POST','/api/data','HTTP/1.1','localhost','Python-urllib/3.9',NULL,NULL,'{\"data\":\"sensitive\"}',201,'Location: /api/data/1',NULL,'2024-01-15 10:00:20')");
    }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM security_events");
    if ($r && (int)$r->fetch_assoc()['cnt'] === 0) {
        $conn->query("INSERT INTO security_events (id,event_type,severity,source_ip,destination_ip,description,timestamp,flag) VALUES
            (1,'Port Scan','Medium','192.168.1.105','192.168.1.200','端口扫描检测','2024-01-15 09:30:00',NULL),
            (2,'SQL Injection','High','192.168.1.106','192.168.1.200','SQL注入尝试','2024-01-15 09:35:00',NULL),
            (3,'XSS Attempt','High','192.168.1.107','192.168.1.200','XSS攻击尝试','2024-01-15 09:40:00',NULL),
            (4,'Brute Force','High','192.168.1.108','192.168.1.200','暴力破解攻击','2024-01-15 09:45:00',NULL),
            (5,'Data Exfiltration','Critical','192.168.1.109','45.33.32.156','数据泄露检测','2024-01-15 09:50:00','flag{security_analysis_expert_2024}')");
    }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM network_sessions");
    if ($r && (int)$r->fetch_assoc()['cnt'] === 0) {
        $conn->query("INSERT INTO network_sessions (id,session_id,source_ip,destination_ip,protocol,source_port,destination_port,start_time,end_time,duration,packet_count,byte_count,status) VALUES
            (1,'S001','192.168.1.100','192.168.1.200','TCP','49152','80','2024-01-15 10:30:00.123456','2024-01-15 10:30:11.000000','10.876544s',15,1200,'Closed'),
            (2,'S002','192.168.1.100','192.168.1.200','TCP','49153','443','2024-01-15 10:31:00.000000',NULL,NULL,8,800,'Active'),
            (3,'S003','10.0.0.5','10.0.0.10','UDP','53','53','2024-01-15 10:30:01.000000','2024-01-15 10:30:01.000123','0.000123s',2,174,'Closed')");
    }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM users");
    if ($r && (int)$r->fetch_assoc()['cnt'] === 0) {
        $conn->query("INSERT INTO users (id,username,password,email,role) VALUES
            (1,'admin','admin123','admin@protocol-lab.com','admin'),
            (2,'analyst','analyst2024','analyst@protocol-lab.com','user'),
            (3,'guest','guest','guest@protocol-lab.com','user')");
    }
}
ensureDbInitialized($conn);

// Level config: title / timer(s) / difficulty tag
$levels = [
    1 => [
        'title'       => 'Level 1 — TCP/IP 协议分析',
        'timer'       => 600,
        'diff'        => 'Easy',
        'badge_bg'    => '#dcfce7',
        'badge_color' => '#16a34a',
        'desc'        => '网络管理员捕获了一组 TCP/IP 数据包，你需要分析这些数据包，理解 TCP 三次握手过程、识别各层协议特征，并找出关键的网络会话信息。',
        'goal'        => '分析数据包，找出 TCP 三次握手的完整过程，并识别所有网络协议类型',
        'scenario'    => '数据包分析',
        'placeholder' => '输入协议类型筛选（如: TCP）',
        'field'       => 'protocol',
        'tips'        => ['观察 SYN、SYN-ACK、ACK 标志位理解三次握手', '识别 TCP、UDP、ARP、HTTP 等不同协议特征', '分析源IP和目的IP的通信模式', '查看数据包长度和端口信息'],
    ],
    2 => [
        'title'       => 'Level 2 — HTTP 协议分析',
        'timer'       => 900,
        'diff'        => 'Medium',
        'badge_bg'    => '#fef3c7',
        'badge_color' => '#d97706',
        'desc'        => 'Web 服务器日志中记录了若干 HTTP 请求，其中包含敏感信息。你需要分析这些请求，提取登录凭证、会话 Cookie，并找到隐藏在响应中的秘密信息。',
        'goal'        => '分析 HTTP 请求日志，提取敏感信息，找到隐藏的 Flag',
        'scenario'    => 'HTTP 日志分析',
        'placeholder' => '输入路径或方法筛选（如: login）',
        'field'       => 'path',
        'tips'        => ['分析请求方法（GET/POST）和路径', '查看 Cookie 字段中的会话信息', '检查 POST 请求体中的表单数据', '仔细分析响应体中的 JSON 数据'],
    ],
    3 => [
        'title'       => 'Level 3 — 网络安全分析',
        'timer'       => 1200,
        'diff'        => 'Hard',
        'badge_bg'    => '#fee2e2',
        'badge_color' => '#dc2626',
        'desc'        => '安全监控系统检测到多起安全事件，包括端口扫描、SQL注入、XSS攻击和数据泄露。你需要分析这些安全事件，识别攻击模式，并找到被攻击者窃取的敏感 Flag。',
        'goal'        => '分析安全事件日志，识别攻击类型，找到数据泄露事件中的 Flag',
        'scenario'    => '安全事件分析',
        'placeholder' => '输入严重级别筛选（如: Critical）',
        'field'       => 'severity',
        'tips'        => ['按严重级别筛选安全事件', '关注 Critical 和 High 级别的事件', '分析事件描述中的攻击特征', '在数据泄露事件中查找隐藏的 Flag'],
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
$analysisDetected = false;

// Level 1: TCP/IP Protocol Analysis
if ($level === 1 && isset($_GET['protocol']) && $_GET['protocol'] !== '') {
    $input = $_GET['protocol'];
    $query = "SELECT id, timestamp, source_ip, destination_ip, protocol, source_port, destination_port, length, flags, info FROM packets WHERE protocol LIKE '%$input%'";
    $res   = @$conn->query($query);
    if ($res) {
        while ($r = $res->fetch_assoc()) $results[] = $r;
        $analysisDetected = true;
        $tcpCount = 0;
        $synCount = 0;
        $ackCount = 0;
        foreach ($results as $row) {
            if ($row['protocol'] === 'TCP') $tcpCount++;
            if (strpos($row['flags'], 'SYN') !== false) $synCount++;
            if (strpos($row['flags'], 'ACK') !== false) $ackCount++;
        }
        if ($tcpCount >= 3 && $synCount >= 2 && $ackCount >= 2) $success = true;
    } else {
        $error = $conn->error;
        $analysisDetected = true;
    }

// Level 2: HTTP Analysis
} elseif ($level === 2 && isset($_GET['path']) && $_GET['path'] !== '') {
    $input = $_GET['path'];
    $query = "SELECT id, method, path, protocol, host, cookie, body, status_code, response_body, captured_at FROM http_requests WHERE path LIKE '%$input%' OR method LIKE '%$input%'";
    $res   = @$conn->query($query);
    if ($res) {
        while ($r = $res->fetch_assoc()) $results[] = $r;
        $analysisDetected = true;
        foreach ($results as $row) {
            if (preg_match('/flag\{[^\}]+\}/', (string)$row['cookie'], $m) || 
                preg_match('/flag\{[^\}]+\}/', (string)$row['response_body'], $m)) {
                $flagFound = true; $success = true;
            }
        }
        if (!$flagFound && count($results) >= 2) $success = true;
    } else {
        $error = $conn->error;
        $analysisDetected = true;
    }

// Level 3: Security Analysis
} elseif ($level === 3 && isset($_GET['severity']) && $_GET['severity'] !== '') {
    $input = $_GET['severity'];
    $query = "SELECT id, event_type, severity, source_ip, destination_ip, description, timestamp, flag FROM security_events WHERE severity LIKE '%$input%'";
    $res   = @$conn->query($query);
    if ($res) {
        while ($r = $res->fetch_assoc()) $results[] = $r;
        $analysisDetected = true;
        foreach ($results as $row) {
            if (!empty($row['flag']) && strpos($row['flag'], 'flag{') !== false) {
                $flagFound = true; $success = true;
            }
        }
        if (!$flagFound && count($results) >= 2) $success = true;
    } else {
        $error = $conn->error;
        $analysisDetected = true;
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
    $kws  = ['SELECT','FROM','WHERE','AND','OR','LIKE','INSERT','UPDATE','DELETE','information_schema','NULL','ORDER','BY','LIMIT'];
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
<title>Protocol Analysis Lab — <?php echo htmlspecialchars($cfg['title']); ?></title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<style>
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

.wrap{max-width:920px;margin:0 auto;padding:28px 20px 100px}

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

.badge{
  display:inline-flex;align-items:center;gap:4px;
  padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:700;
}

.goal-bar{
  background:var(--primary-light);
  border-left:3px solid var(--primary);
  padding:10px 16px;border-radius:0 8px 8px 0;
  margin:16px 0 20px;font-size:.85rem;color:var(--text2);
}
.goal-bar strong{color:var(--primary)}

.sec-label{
  font-size:.72rem;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px;
  display:flex;align-items:center;gap:6px;
}
.sec-label::before{content:'';display:block;width:3px;height:14px;
  background:var(--primary);border-radius:2px}

.input-row{display:flex;gap:8px;align-items:stretch;flex-wrap:wrap}
.input-row input[type=text]{
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

.inj-strip{
  display:flex;align-items:center;gap:8px;
  padding:8px 14px;border-radius:8px;
  font-size:.82rem;font-weight:500;margin-top:14px;
}
.inj-strip.detected{
  background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;
}
.inj-strip.clean{
  background:var(--success-light);border:1px solid #a7f3d0;color:#065f46;
}

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

.empty-msg{color:var(--muted);font-size:.85rem;text-align:center;padding:20px 0}
.err-box{
  color:#991b1b;background:#fef2f2;
  border:1px solid #fecaca;border-radius:8px;
  padding:12px 16px;font-size:.84rem;
  font-family:'Fira Code',monospace;
}
.err-box strong{display:block;margin-bottom:4px}

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

.packet-preview{
  background:#0f172a;
  border:1px solid #334155;
  border-radius:8px;padding:12px 14px;
  font-family:'Fira Code',monospace;
  font-size:.78rem;line-height:1.6;
  color:#e2e8f0;
  overflow-x:auto;
}
.packet-preview .packet-line{margin-bottom:4px}
.packet-preview .packet-line:last-child{margin-bottom:0}
.packet-preview .packet-field{color:#38bdf8}
.packet-preview .packet-value{color:#f1f5f9}
.packet-preview .packet-highlight{color:#f59e0b;font-weight:bold}
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">
    <div class="logo-icon">P</div>
    Protocol <em>Analysis</em>&nbsp;Lab
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

<div class="wrap">

  <div class="progress-steps">
    <?php foreach ($levels as $i => $l): ?>
    <div class="p-step <?php echo $i < $level ? 'done' : ($i === $level ? 'active' : ''); ?>">
      <div class="p-dot"><?php echo $i < $level ? '✓' : $i; ?></div>
      <div class="p-label"><?php echo $l['diff']; ?></div>
    </div>
    <?php endforeach; ?>
  </div>

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

    <?php if ($level === 1): ?>
    <div class="sec-label">数据包筛选器</div>
    <form method="get">
      <input type="hidden" name="level" value="1">
      <div class="input-row">
        <input type="text" name="protocol"
               placeholder="<?php echo htmlspecialchars($cfg['placeholder']); ?>"
               value="<?php echo isset($_GET['protocol'])?htmlspecialchars($_GET['protocol']):''; ?>"
               autocomplete="off" spellcheck="false">
        <button type="submit">🔍 筛选数据包</button>
      </div>
    </form>

    <?php elseif ($level === 2): ?>
    <div class="sec-label">HTTP 请求日志筛选</div>
    <form method="get">
      <input type="hidden" name="level" value="2">
      <div class="input-row">
        <input type="text" name="path"
               placeholder="<?php echo htmlspecialchars($cfg['placeholder']); ?>"
               value="<?php echo isset($_GET['path'])?htmlspecialchars($_GET['path']):''; ?>"
               autocomplete="off" spellcheck="false">
        <button type="submit">🔍 分析请求</button>
      </div>
    </form>

    <?php else: ?>
    <div class="sec-label">安全事件筛选</div>
    <form method="get">
      <input type="hidden" name="level" value="3">
      <div class="input-row">
        <input type="text" name="severity"
               placeholder="<?php echo htmlspecialchars($cfg['placeholder']); ?>"
               value="<?php echo isset($_GET['severity'])?htmlspecialchars($_GET['severity']):''; ?>"
               autocomplete="off" spellcheck="false">
        <button type="submit">🔍 分析事件</button>
      </div>
    </form>
    <?php endif; ?>

    <?php if (!empty($input) && $analysisDetected): ?>
    <div class="inj-strip detected">
      🔍 检测到分析操作，正在处理数据...
    </div>
    <?php elseif (!empty($input) && !$analysisDetected): ?>
    <div class="inj-strip clean">
      ✅ 正常查询
    </div>
    <?php endif; ?>

    <button class="tips-toggle" onclick="toggleTips()">
      💡 <span id="tips-btn-text">显示提示</span>
    </button>
    <ul class="tips-list" id="tips-list">
      <?php foreach ($cfg['tips'] as $t): ?>
      <li><?php echo $t; ?></li>
      <?php endforeach; ?>
    </ul>
  </div>

  <?php if ($query): ?>
  <div class="card">
    <div class="sec-label">查询语句</div>
    <div class="sql-box"><?php echo highlightSQL($query, $input); ?></div>
  </div>
  <?php endif; ?>

  <?php if ($success && !$flagFound): ?>
  <div class="success-banner">
    <h3>🎉 分析成功！</h3>
    <p style="font-size:.88rem;color:#065f46;margin-top:4px;line-height:1.6">
      你成功完成了 <strong><?php echo htmlspecialchars($cfg['title']); ?></strong> 的分析任务！
    </p>
    <?php if ($level < 3): ?>
    <a href="?level=<?php echo $level+1; ?>" class="next-btn">
      进入 Level <?php echo $level+1; ?> →
    </a>
    <?php endif; ?>
  </div>
  <?php endif; ?>

  <?php if ($flagFound && $flagText): ?>
  <div class="flag-box">
    <h2>🏁 全关通关！Flag 获取成功</h2>
    <p style="font-size:.88rem;color:#065f46;margin-bottom:16px">
      你成功分析了所有协议数据并找到了隐藏的 Flag，请将 Flag 提交到实训平台。
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

  <?php if (!empty($results)): ?>
  <div class="card">
    <div class="sec-label">
      分析结果
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
  <div class="card"><p class="empty-msg">🔍 未查询到匹配记录，请调整筛选条件重试。</p></div>
  <?php endif; ?>

  <?php if ($level === 1 && !$query): ?>
  <div class="card">
    <div class="sec-label">📊 数据包预览</div>
    <div class="packet-preview">
      <div class="packet-line"><span class="packet-field">时间戳:</span> <span class="packet-value">2024-01-15 10:30:00.123456</span></div>
      <div class="packet-line"><span class="packet-field">源IP:</span> <span class="packet-value">192.168.1.100</span> <span class="packet-field">→</span> <span class="packet-value">192.168.1.200</span></div>
      <div class="packet-line"><span class="packet-field">协议:</span> <span class="packet-value">TCP</span> <span class="packet-field">端口:</span> <span class="packet-value">49152 → 80</span></div>
      <div class="packet-line"><span class="packet-field">标志位:</span> <span class="packet-highlight">SYN</span> <span class="packet-field">长度:</span> <span class="packet-value">60 bytes</span></div>
      <div class="packet-line"><span class="packet-field">信息:</span> <span class="packet-value">TCP SYN - 三次握手第一步</span></div>
    </div>
    <p style="color:var(--muted);font-size:.82rem;margin-top:12px">提示：输入协议类型（如 TCP、UDP、HTTP、ARP）进行筛选分析</p>
  </div>
  <?php endif; ?>

  <?php if ($level === 2 && !$query): ?>
  <div class="card">
    <div class="sec-label">📋 HTTP 请求预览</div>
    <div class="packet-preview">
      <div class="packet-line"><span class="packet-field">方法:</span> <span class="packet-highlight">POST</span> <span class="packet-field">路径:</span> <span class="packet-value">/login</span></div>
      <div class="packet-line"><span class="packet-field">协议:</span> <span class="packet-value">HTTP/1.1</span> <span class="packet-field">状态码:</span> <span class="packet-value">200</span></div>
      <div class="packet-line"><span class="packet-field">主机:</span> <span class="packet-value">localhost</span></div>
      <div class="packet-line"><span class="packet-field">请求体:</span> <span class="packet-value">username=admin&password=secret123</span></div>
      <div class="packet-line"><span class="packet-field">响应:</span> <span class="packet-value">{"status":"success"}</span></div>
    </div>
    <p style="color:var(--muted);font-size:.82rem;margin-top:12px">提示：输入路径（如 /login、/api/secret）或方法（如 GET、POST）进行筛选分析</p>
  </div>
  <?php endif; ?>

  <?php if ($level === 3 && !$query): ?>
  <div class="card">
    <div class="sec-label">🛡️ 安全事件预览</div>
    <div class="packet-preview">
      <div class="packet-line"><span class="packet-field">事件类型:</span> <span class="packet-highlight">SQL Injection</span></div>
      <div class="packet-line"><span class="packet-field">严重级别:</span> <span class="packet-highlight">High</span></div>
      <div class="packet-line"><span class="packet-field">源IP:</span> <span class="packet-value">192.168.1.106</span> <span class="packet-field">→</span> <span class="packet-value">192.168.1.200</span></div>
      <div class="packet-line"><span class="packet-field">描述:</span> <span class="packet-value">检测到SQL注入尝试</span></div>
      <div class="packet-line"><span class="packet-field">时间:</span> <span class="packet-value">2024-01-15 09:35:00</span></div>
    </div>
    <p style="color:var(--muted);font-size:.82rem;margin-top:12px">提示：输入严重级别（如 Critical、High、Medium）进行筛选分析</p>
  </div>
  <?php endif; ?>

  <?php if ($error): ?>
  <div class="card">
    <div class="err-box">
      <strong>⚡ 查询错误</strong>
      <?php echo htmlspecialchars($error); ?>
    </div>
  </div>
  <?php endif; ?>

</div>

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

<script>
const TIMER_KEY   = 'protocol_timer_lv<?php echo $level; ?>';
const TIMER_SEC   = <?php echo $cfg['timer']; ?>;
const LEVEL       = <?php echo $level; ?>;
const LEVEL_TITLE = <?php echo json_encode($cfg['title']); ?>;

function sendToAgent(payload) {
  window.parent.postMessage(payload, '*');
  fetch('http://192.168.1.106:8010/api/lab/event', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload),
    mode: 'no-cors'
  }).catch(() => {});
}

(function() {
  const navType = (performance.getEntriesByType('navigation')[0] || {}).type || 'navigate';
  const isReload = (navType === 'reload');
  let endTime;
  const stored = sessionStorage.getItem(TIMER_KEY);
  if (isReload && stored) {
    endTime = parseInt(stored);
  } else {
    endTime = Date.now() + TIMER_SEC * 1000;
    sessionStorage.setItem(TIMER_KEY, endTime);
    sendToAgent({
      type: 'lab_opened',
      container: 'protocol-analysis-lab-web-1',
      level: LEVEL,
      levelTitle: LEVEL_TITLE,
      timerSeconds: TIMER_SEC,
      timestamp: new Date().toISOString()
    });
  }
})();

function showHintModal(auto = false, customMsg = '') {
  const overlay = document.getElementById('hint-modal');
  if (!overlay) return;
  const defMsg = auto
    ? `倒计时结束！${LEVEL_TITLE} 是否需要 AI 助手分析你的操作日志并给出阶梯式提示？`
    : `是否需要 AI 助手分析你的操作，并为 ${LEVEL_TITLE} 给出阶梯式提示？`;
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
    container: 'protocol-analysis-lab-web-1',
    level: LEVEL,
    levelTitle: LEVEL_TITLE,
    timestamp: new Date().toISOString(),
    prompt: `请分析 protocol-analysis-lab-web-1 容器的操作，判断学生在"${LEVEL_TITLE}"的当前进度，并给出阶梯式提示（先给最小提示，如仍需要再给下一步）。请使用中文。`
  };
  window.parent.postMessage(payload, '*');
  fetch('http://192.168.1.106:8010/api/lab/event', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload),
    mode: 'no-cors'
  }).catch(() => {});
}

function toggleTips() {
  const list = document.getElementById('tips-list');
  const btn  = document.getElementById('tips-btn-text');
  if (!list || !btn) return;
  const open = list.classList.toggle('open');
  btn.textContent = open ? '隐藏提示' : '显示提示';
}

function copyFlag(text) {
  navigator.clipboard.writeText(text).then(() => {
    const el = document.getElementById('copy-ok');
    if (el) { el.style.opacity = '1'; setTimeout(() => el.style.opacity = '0', 2500); }
  });
}
</script>

</body>
</html>