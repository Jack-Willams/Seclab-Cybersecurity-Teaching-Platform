# SecLab 安全实验环境

这是一个包含5个不同安全漏洞实验的Docker环境集合，用于学习和研究Web安全漏洞。

## 实验环境列表

1. **SQL注入实验** (端口8091) - `sqli-lab/`
2. **XSS跨站脚本攻击实验** (端口8092) - `xss-lab/`
3. **CSRF跨站请求伪造实验** (端口8093) - `csrf-lab/`
4. **文件上传漏洞实验** (端口8094) - `file-upload-lab/`
5. **目录遍历漏洞实验** (端口8095) - `directory-traversal-lab/`

## 快速开始

### 启动所有实验环境
```bash
# Windows
start-all-labs.bat

# Linux/Mac
./start-all-labs.sh
```

### 停止所有实验环境
```bash
# Windows
stop-all-labs.bat

# Linux/Mac
./stop-all-labs.sh
```

### 单独启动某个实验
```bash
cd [实验目录]
docker-compose up -d
```

### 单独停止某个实验
```bash
cd [实验目录]
docker-compose down
```

## 访问地址

启动后，可以通过以下地址访问各个实验环境：

- **SQL注入实验**: http://localhost:8091
- **XSS实验**: http://localhost:8092
- **CSRF实验**: http://localhost:8093
- **文件上传实验**: http://localhost:8094
- **目录遍历实验**: http://localhost:8095

## 实验环境详情

### 1. SQL注入实验 (sqli-lab)
- **端口**: 8091
- **功能**: 模拟存在SQL注入漏洞的登录系统
- **测试账户**: admin/admin123, user1/password123
- **漏洞类型**: 数字型、字符型SQL注入

### 2. XSS跨站脚本攻击实验 (xss-lab)
- **端口**: 8092
- **功能**: 留言板系统，存在XSS漏洞
- **测试账户**: admin/admin123, user1/password123
- **漏洞类型**: 反射型XSS、存储型XSS

### 3. CSRF跨站请求伪造实验 (csrf-lab)
- **端口**: 8093
- **功能**: 银行转账系统，存在CSRF漏洞
- **测试账户**: alice/alice123, bob/bob123, attacker/attacker123
- **漏洞类型**: CSRF攻击

### 4. 文件上传漏洞实验 (file-upload-lab)
- **端口**: 8094
- **功能**: 文件上传系统，存在文件上传漏洞
- **测试账户**: admin/admin123, user1/password123
- **漏洞类型**: 文件上传绕过、Web Shell上传

### 5. 目录遍历漏洞实验 (directory-traversal-lab)
- **端口**: 8095
- **功能**: 文件查看系统，存在目录遍历漏洞
- **测试账户**: admin/admin123, user1/password123
- **漏洞类型**: 路径遍历、敏感文件读取

## 系统要求

- Docker
- Docker Compose
- 至少4GB可用内存
- 至少10GB可用磁盘空间

## 安全警告

⚠️ **重要提醒**：
- 这些实验环境仅用于学习和研究目的
- 包含故意设计的安全漏洞
- 请勿在生产环境中使用
- 请勿在公网环境中部署
- 仅限在安全的本地环境中使用

## 故障排除

### 端口冲突
如果遇到端口冲突，可以修改各个实验目录中的 `docker-compose.yml` 文件，更改端口映射。

### 容器启动失败
1. 检查Docker服务是否正常运行
2. 检查端口是否被占用
3. 检查磁盘空间是否充足
4. 查看容器日志：`docker-compose logs`

### 数据库连接失败
1. 等待数据库容器完全启动（通常需要30-60秒）
2. 检查数据库容器状态：`docker-compose ps`
3. 重启数据库容器：`docker-compose restart db`

## 开发说明

### 添加新的实验环境
1. 创建新的实验目录
2. 复制现有实验的 `docker-compose.yml` 和 `Dockerfile`
3. 修改端口映射避免冲突
4. 创建相应的Web应用和数据库初始化脚本
5. 更新启动脚本

### 修改现有实验
- Web应用代码位于各实验目录的 `web/` 文件夹
- 数据库初始化脚本位于各实验目录的 `init.sql`
- Docker配置位于各实验目录的 `docker-compose.yml` 和 `Dockerfile`

## 许可证

本项目仅用于教育和研究目的。 