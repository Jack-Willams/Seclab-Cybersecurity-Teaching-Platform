const express = require('express');
const { exec } = require('child_process');
const cors = require('cors');
const path = require('path');
const http = require('http');
const https = require('https');
const net = require('net');
const util = require('util');

const app = express();
const port = 3000;
const ROOT_DIR = __dirname;
const CONTAINER_NAME_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_.-]+$/;
const execAsync = util.promisify(exec);
const HEALTHY_HTTP_STATUS = new Set([200, 301, 302, 403]);

const LABS = {
  sqli: {
    composePath: 'sqli-lab\\docker-compose.yml',
    defaultUrl: 'http://localhost:8091/index.php',
  },
  xss: {
    composePath: 'xss-lab\\docker-compose.yml',
    defaultUrl: 'http://localhost:8092/index.php',
  },
  csrf: {
    composePath: 'csrf-lab\\docker-compose.yml',
    defaultUrl: 'http://localhost:8093/index.php',
  },
  cmd: {
    composePath: 'command-inject\\docker-compose.yml',
    defaultUrl: 'http://localhost:8090/index.php',
  },
  upload: {
    composePath: 'file-upload-lab\\docker-compose.yml',
    defaultUrl: 'http://localhost:8094/index.php',
  },
  dir: {
    composePath: 'directory-traversal-lab\\docker-compose.yml',
    defaultUrl: 'http://localhost:8095/index.php',
  },
  // 栈溢出 pwn 靶机：socat 暴露 TCP:70（host 8096），非 Web，学生在操作桌面用 nc/pwntools 连接
  stack: {
    composePath: 'stack-overflow-lab\\docker-compose.yml',
    defaultUrl: 'nc stack-overflow-lab-web-1 70',
  },
  // 协议分析靶场：三关（TCP/IP 分析 → HTTP 分析 → 安全事件分析），host 端口 8896
  protocol: {
    composePath: 'protocol-analysis-lab\\docker-compose.yml',
    defaultUrl: 'http://localhost:8896/index.php',
  },
};

app.use(cors());
app.use(express.json());

function runCommand(command, res, options = {}) {
  exec(command, { cwd: ROOT_DIR, ...options }, (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({
        isSuccess: 0,
        status: 500,
        message: stderr || error.message || '命令执行失败',
        data: null,
      });
      return;
    }

    res.json({
      isSuccess: 1,
      status: 200,
      message: 'success',
      data: {
        stdout: stdout.trim(),
        stderr: stderr.trim(),
      },
    });
  });
}

function validateContainerName(containerName) {
  return CONTAINER_NAME_PATTERN.test(String(containerName || '').trim());
}

function quotedWorkdir(relativeDir) {
  return `"${path.join(ROOT_DIR, relativeDir)}"`;
}

function buildUrlWithPort(defaultUrl, hostPort) {
  const parsed = new URL(defaultUrl);
  parsed.hostname = 'localhost';
  parsed.port = String(hostPort);
  return parsed.toString();
}

function parsePublishedPort(stdout) {
  const line = String(stdout || '').trim().split(/\r?\n/).find(Boolean);
  if (!line) return null;
  const match = line.match(/:(\d+)$/);
  return match ? Number(match[1]) : null;
}

async function getComposeContainerId(relativeComposePath) {
  const { stdout } = await execAsync(`docker compose -f ${quotedWorkdir(relativeComposePath)} ps -q web`, { cwd: ROOT_DIR });
  return String(stdout || '').trim();
}

async function inspectContainerRunning(containerId) {
  if (!containerId) return false;
  const { stdout } = await execAsync(`docker inspect --format "{{.State.Running}}" ${containerId}`, { cwd: ROOT_DIR });
  return String(stdout || '').trim() === 'true';
}

async function getPublishedHostPort(relativeComposePath) {
  const { stdout } = await execAsync(`docker compose -f ${quotedWorkdir(relativeComposePath)} port web 80`, { cwd: ROOT_DIR });
  return parsePublishedPort(stdout);
}

function checkPortListening(host, hostPort, timeoutMs = 1200) {
  return new Promise((resolve) => {
    if (!hostPort) {
      resolve(false);
      return;
    }

    const socket = net.createConnection({ host, port: hostPort });
    const finish = (isListening) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(isListening);
    };

    socket.setTimeout(timeoutMs);
    socket.once('connect', () => finish(true));
    socket.once('timeout', () => finish(false));
    socket.once('error', () => finish(false));
  });
}

function probeHttpUrl(url, timeoutMs = 2000) {
  return new Promise((resolve) => {
    const parsed = new URL(url);
    const client = parsed.protocol === 'https:' ? https : http;
    const request = client.get(url, { timeout: timeoutMs }, (response) => {
      response.resume();
      const httpStatus = response.statusCode || 0;
      resolve({
        httpReachable: HEALTHY_HTTP_STATUS.has(httpStatus),
        httpStatus,
        error: null,
      });
    });

    request.once('timeout', () => {
      request.destroy();
      resolve({ httpReachable: false, httpStatus: null, error: 'URL 暂不可访问' });
    });
    request.once('error', (error) => {
      resolve({ httpReachable: false, httpStatus: null, error: error.code || error.message || 'URL 暂不可访问' });
    });
  });
}

function buildTargetStatus({ labKey, containerId, containerRunning, hostPort, portListening, targetUrl, httpReachable, httpStatus, probeError }) {
  let status = 'offline';
  let message = '靶机容器不存在';
  let reason = 'container_missing';

  if (containerId && !containerRunning) {
    message = '靶机容器未运行';
    reason = 'container_not_running';
  } else if (containerRunning && !hostPort) {
    status = 'starting';
    message = '靶机 Web 端口未发布';
    reason = 'port_not_published';
  } else if (containerRunning && !portListening) {
    status = 'starting';
    message = '端口未监听';
    reason = 'port_not_listening';
  } else if (containerRunning && portListening && !httpReachable) {
    status = 'starting';
    message = probeError === 'ECONNREFUSED' ? '靶机 Web 服务尚未启动' : 'URL 暂不可访问';
    reason = 'http_probe_failed';
  } else if (containerRunning && portListening && httpReachable) {
    status = 'online';
    message = '靶机 Web 服务可访问';
    reason = 'ok';
  }

  return {
    lab: labKey,
    containerId,
    containerExists: Boolean(containerId),
    containerRunning,
    hostPort,
    portListening,
    targetUrl,
    httpReachable,
    httpStatus,
    status,
    message,
    reason,
  };
}

async function getTargetStatus(labKey) {
  const lab = LABS[labKey];
  if (!lab) {
    const error = new Error('未知靶机类型');
    error.statusCode = 400;
    throw error;
  }

  let containerId = '';
  let containerRunning = false;
  let hostPort = null;
  let targetUrl = lab.defaultUrl;

  try {
    containerId = await getComposeContainerId(lab.composePath);
  } catch (_error) {
    containerId = '';
  }

  try {
    containerRunning = await inspectContainerRunning(containerId);
  } catch (_error) {
    containerRunning = false;
  }

  try {
    hostPort = await getPublishedHostPort(lab.composePath);
  } catch (_error) {
    hostPort = null;
  }

  if (hostPort) {
    targetUrl = buildUrlWithPort(lab.defaultUrl, hostPort);
  }

  const portListening = containerRunning && hostPort
    ? await checkPortListening('127.0.0.1', hostPort)
    : false;
  const probe = portListening
    ? await probeHttpUrl(targetUrl)
    : { httpReachable: false, httpStatus: null, error: null };

  return buildTargetStatus({
    labKey,
    containerId,
    containerRunning,
    hostPort,
    portListening,
    targetUrl,
    httpReachable: probe.httpReachable,
    httpStatus: probe.httpStatus,
    probeError: probe.error,
  });
}

async function waitForTargetStatus(labKey, attempts = 6, intervalMs = 1000) {
  let latest = await getTargetStatus(labKey);
  for (let index = 1; index < attempts && latest.status !== 'online'; index += 1) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    latest = await getTargetStatus(labKey);
  }
  return latest;
}

function startComposeLab(labKey, res) {
  const lab = LABS[labKey];
  if (!lab) {
    res.status(400).json({
      isSuccess: 0,
      status: 400,
      message: '未知靶机类型',
      data: null,
    });
    return;
  }

  exec(`docker compose -f ${quotedWorkdir(lab.composePath)} up -d`, { cwd: ROOT_DIR }, async (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({
        isSuccess: 0,
        status: 500,
        message: stderr || '启动实验容器失败',
        data: null,
      });
      return;
    }

    const targetStatus = await waitForTargetStatus(labKey);
    res.json({
      isSuccess: 1,
      status: 200,
      message: targetStatus.status === 'online' ? '启动实验容器成功' : targetStatus.message,
      data: {
        url: targetStatus.status === 'online' ? targetStatus.targetUrl : null,
        targetUrl: targetStatus.targetUrl,
        ...targetStatus,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
      },
    });
  });
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', message: 'Docker API服务器正常运行' });
});

app.get('/api/docker/status', (_req, res) => {
  exec('docker ps -a --format "{{.Names}},{{.Status}},{{.Ports}}"', { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({
        isSuccess: 0,
        status: 500,
        message: stderr || '获取容器状态失败',
        data: null,
      });
      return;
    }

    const containers = stdout.trim()
      ? stdout.trim().split('\n').map((line) => {
          const [name, status, ports] = line.split(',');
          return { name, status, ports };
        })
      : [];

    res.json({
      isSuccess: 1,
      status: 200,
      message: '获取容器状态成功',
      data: containers,
    });
  });
});

app.get('/api/docker/target-status/:lab', async (req, res) => {
  try {
    const targetStatus = await getTargetStatus(String(req.params.lab || '').trim());
    res.json({
      isSuccess: 1,
      status: 200,
      message: targetStatus.message,
      data: targetStatus,
    });
  } catch (error) {
    res.status(error.statusCode || 500).json({
      isSuccess: 0,
      status: error.statusCode || 500,
      message: error.message || '获取靶机状态失败',
      data: null,
    });
  }
});

app.post('/api/docker/start-sqli', (_req, res) => {
  startComposeLab('sqli', res);
});

app.post('/api/docker/start-xss', (_req, res) => {
  startComposeLab('xss', res);
});

app.post('/api/docker/start-csrf', (_req, res) => {
  startComposeLab('csrf', res);
});

app.post('/api/docker/start-cmd', (_req, res) => {
  startComposeLab('cmd', res);
});

app.post('/api/docker/start-upload', (_req, res) => {
  startComposeLab('upload', res);
});

app.post('/api/docker/start-dir', (_req, res) => {
  startComposeLab('dir', res);
});

app.post('/api/docker/start-stack', (_req, res) => {
  startComposeLab('stack', res);
});

app.post('/api/docker/start-protocol', (_req, res) => {
  startComposeLab('protocol', res);
});

app.post('/api/docker/start-sec-code', (_req, res) => {
  exec('docker run -d --name sec-code-container -p 8080:80 gsycl2004/sec-code', { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({
        isSuccess: 0,
        status: 500,
        message: stderr || '启动安全代码容器失败',
        data: null,
      });
      return;
    }

    res.json({
      isSuccess: 1,
      status: 200,
      message: '启动安全代码容器成功',
      data: {
        url: 'http://localhost:8080',
        stdout: stdout.trim(),
        stderr: stderr.trim(),
      },
    });
  });
});

app.post('/api/docker/stop-all', (_req, res) => {
  runCommand('.\\stop-all-services.bat', res, { shell: true });
});

app.get('/api/docker/list', (_req, res) => {
  exec('docker ps -a --format "{{.Names}},{{.Status}}"', { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({ success: false, error: stderr || '获取容器列表失败' });
      return;
    }

    const containers = stdout.trim()
      ? stdout.trim().split('\n').map((line) => {
          const [name, status] = line.split(',');
          return { name, status };
        })
      : [];

    res.json({ success: true, data: containers });
  });
});

app.get('/api/docker/containers', (req, res) => {
  const containerName = String(req.query.name || '').trim();
  if (!containerName) {
    exec('docker ps -a --format "{{.Names}},{{.Status}}"', { cwd: ROOT_DIR }, (error, stdout, stderr) => {
      if (error) {
        res.status(500).json({ success: false, error: stderr || '获取容器列表失败' });
        return;
      }

      const containers = stdout.trim()
        ? stdout.trim().split('\n').map((line) => {
            const [name, status] = line.split(',');
            return { name, status };
          })
        : [];

      res.json({ success: true, data: containers });
    });
    return;
  }

  if (!validateContainerName(containerName)) {
    res.status(400).json({ success: false, error: '非法容器名称' });
    return;
  }

  exec(`docker inspect --format "{{.Name}},{{.State.Status}},{{.State.StartedAt}}" ${containerName}`, { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(404).json({ success: false, error: stderr || `容器 '${containerName}' 不存在` });
      return;
    }

    const [name, status, startedAt] = stdout.trim().split(',');
    res.json({
      success: true,
      data: {
        name: String(name || '').replace(/^\//, ''),
        status,
        started_at: startedAt,
      },
    });
  });
});

app.get('/api/docker/logs/:container_name', (req, res) => {
  const containerName = String(req.params.container_name || '').trim();
  const tail = Number(req.query.tail || 100);

  if (!validateContainerName(containerName)) {
    res.status(400).json({ success: false, error: '非法容器名称' });
    return;
  }

  exec(`docker logs --tail ${Number.isFinite(tail) ? tail : 100} ${containerName}`, { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(404).json({ success: false, error: stderr || `容器 '${containerName}' 不存在或未运行` });
      return;
    }

    res.json({ success: true, container: containerName, logs: `${stdout}${stderr}` });
  });
});

app.post('/api/docker/exec/:container_name', (req, res) => {
  const containerName = String(req.params.container_name || '').trim();
  const command = String(req.body.command || '').trim();

  if (!validateContainerName(containerName)) {
    res.status(400).json({ success: false, error: '非法容器名称' });
    return;
  }

  if (!command) {
    res.status(400).json({ success: false, error: '缺少 command 参数' });
    return;
  }

  exec(`docker exec ${containerName} ${command}`, { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({ success: false, error: stderr || error.message });
      return;
    }

    res.json({
      success: true,
      container: containerName,
      command,
      exit_code: 0,
      output: `${stdout}${stderr}`,
    });
  });
});

app.post('/api/docker/stop/:container_name', (req, res) => {
  const containerName = String(req.params.container_name || '').trim();
  if (!validateContainerName(containerName)) {
    res.status(400).json({ success: false, error: '非法容器名称' });
    return;
  }

  exec(`docker stop ${containerName}`, { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({ success: false, error: stderr || error.message });
      return;
    }

    res.json({ success: true, message: `容器 '${containerName}' 已停止`, data: stdout.trim() });
  });
});

app.post('/api/docker/start/:container_name', (req, res) => {
  const containerName = String(req.params.container_name || '').trim();
  if (!validateContainerName(containerName)) {
    res.status(400).json({ success: false, error: '非法容器名称' });
    return;
  }

  exec(`docker start ${containerName}`, { cwd: ROOT_DIR }, (error, stdout, stderr) => {
    if (error) {
      res.status(500).json({ success: false, error: stderr || error.message });
      return;
    }

    res.json({ success: true, message: `容器 '${containerName}' 已启动`, data: stdout.trim() });
  });
});

app.listen(port, () => {
  console.log(`Docker API服务器运行在 http://localhost:${port}`);
});
