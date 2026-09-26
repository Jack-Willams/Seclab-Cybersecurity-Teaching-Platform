# 图床服务 (Image Service)

一个基于Spring Boot和Kotlin的简单图床服务，提供图片上传、存储、查看和下载功能。

## 功能特点

- 图片上传与存储
- 图片预览与查看
- 图片下载
- 图片管理（查看列表，删除等）
- 美观的用户界面
- 支持拖拽上传

## 技术栈

- Kotlin 1.9.22
- Spring Boot 3.2.3
- Spring Data JPA
- MariaDB
- HTML/CSS/JavaScript

## 快速开始

### 环境要求

- JDK 17+
- MariaDB 10.x

### 数据库配置

1. 创建名为`imagedb`的数据库：

```sql
CREATE DATABASE imagedb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 在`application.properties`中根据你的环境配置数据库连接：

```properties
spring.datasource.url=jdbc:mariadb://localhost:3306/imagedb?useUnicode=true&characterEncoding=utf8&useSSL=false
spring.datasource.username=你的用户名
spring.datasource.password=你的密码
```

### 运行应用

```bash
# 使用Gradle运行应用
./gradlew bootRun

# 或者构建并运行JAR文件
./gradlew build
java -jar build/libs/image-service-0.0.1-SNAPSHOT.jar
```

应用默认在8080端口运行，访问http://localhost:8080可以打开图床界面。

## API接口

### 上传图片
- **URL**: `/api/images/upload`
- **方法**: POST
- **参数**: `file` (文件，multipart/form-data)
- **返回示例**:
  ```json
  {
    "id": 1,
    "filename": "uuid-filename.jpg",
    "originalFilename": "myimage.jpg",
    "url": "http://localhost:8080/api/images/view/uuid-filename.jpg",
    "size": 125460,
    "contentType": "image/jpeg",
    "uploadTime": "2023-03-23T10:15:30"
  }
  ```

### 获取图片信息
- **URL**: `/api/images/{id}`
- **方法**: GET
- **返回**: 图片详细信息

### 获取所有图片
- **URL**: `/api/images`
- **方法**: GET
- **返回**: 图片列表

### 查看图片
- **URL**: `/api/images/view/{filename}`
- **方法**: GET
- **返回**: 图片文件

### 下载图片
- **URL**: `/api/images/download/{filename}`
- **方法**: GET
- **返回**: 图片文件（附件下载）

### 删除图片
- **URL**: `/api/images/{id}`
- **方法**: DELETE

## 配置选项

可在`application.properties`中配置的主要参数：

- `image.storage.location`: 图片存储的本地目录（默认：upload-dir）
- `image.storage.baseUrl`: 图片访问URL的基础路径
- `server.port`: 应用服务端口
- `spring.servlet.multipart.max-file-size`: 允许上传的最大文件大小
- `spring.servlet.multipart.max-request-size`: 允许的最大请求大小 