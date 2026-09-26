# SecLab 操作环境镜像 — seclab-op-web-tools:1.0

学员实验"操作环境"侧的虚拟桌面容器。基于 debian:12-slim + XFCE + TigerVNC，预装基础 Web 渗透工具：

- 浏览器：Firefox ESR
- Web：curl / wget / sqlmap / dirb / gobuster / ffuf / wfuzz
- 网络：nmap / netcat / tcpdump / dnsutils / whois / traceroute
- 密码：hydra
- 终端：xfce4-terminal、bash、vim、git、python3、ssh client

## 构建

```powershell
.\build.ps1
```

或直接 `docker build -t seclab-op-web-tools:1.0 .`

## 独立测试

```powershell
docker run --rm -p 15901:5901 seclab-op-web-tools:1.0
# 用 VNC 客户端连 localhost:15901，密码 123456
```

## 与 ai-agent-service 协作

正常使用走 `ai-agent-service` 的 `/api/docker/operation/start` 接口；该接口会动态：
1. 启动本镜像，把 5901 映射到随机宿主端口
2. 创建一个 docker network `seclab-op-<sessionId>`
3. 把当前实验对应的靶机容器（如 `sqli-lab-web-1`）`connect` 到该网络
4. 把会话信息写入 `operation_session` 表

学生在桌面里的 Firefox 直接访问容器名 + 80（例如 `http://sqli-lab-web-1`）即可触达靶机。

## 默认凭证

- root 密码：`123456`
- VNC 密码：`123456`

如需改动，重新构建时传 `--build-arg ROOT_PASSWORD=xxx --build-arg VNC_PASSWORD=xxx`。
