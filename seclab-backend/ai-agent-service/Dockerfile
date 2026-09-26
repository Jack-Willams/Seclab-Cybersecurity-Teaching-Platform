FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（docker SDK 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    --default-timeout=120 \
    --retries=10 \
    && python -m pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    --default-timeout=120 \
    --retries=10 \
    -r requirements.txt

COPY . .

EXPOSE 8010

# 生产模式：不开 reload，worker 数由环境变量控制
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "2"]
