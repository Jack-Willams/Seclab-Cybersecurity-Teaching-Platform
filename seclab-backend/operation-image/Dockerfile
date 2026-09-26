FROM debian:12-slim
EXPOSE 5901
WORKDIR /
ARG ROOT_PASSWORD="123456"
ARG VNC_PASSWORD="123456"

RUN echo 'Acquire::https::Verify-Peer "false";' > /etc/apt/apt.conf.d/99ignore-ssl && \
    echo 'Acquire::https::Verify-Host "false";' >> /etc/apt/apt.conf.d/99ignore-ssl

RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    echo "deb https://mirrors.tencent.com/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tencent.com/debian bookworm-updates main" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tencent.com/debian-security bookworm-security main" >> /etc/apt/sources.list

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    tigervnc-standalone-server \
    bash \
    supervisor \
    xfce4 \
    xfce4-terminal \
    dbus-x11 \
    lightdm-gtk-greeter \
    locales \
    fonts-noto-core \
    fonts-noto-cjk && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    sed -i '/zh_CN.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get clean

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN echo "root:${ROOT_PASSWORD}" | chpasswd
RUN mkdir -p /root/.vnc && \
    echo "${VNC_PASSWORD}" | vncpasswd -f > /root/.vnc/passwd && \
    chmod 600 /root/.vnc/passwd

COPY supervisor.conf /etc/supervisor/conf.d/supervisord.conf
COPY set-wallpaper.sh /usr/local/bin/set-wallpaper.sh
COPY restart-panel-on-resize.sh /usr/local/bin/restart-panel-on-resize.sh
COPY wallpapers/ /opt/seclab-wallpapers/
RUN chmod +x /usr/local/bin/set-wallpaper.sh && \
    chmod +x /usr/local/bin/restart-panel-on-resize.sh && \
    cp /opt/seclab-wallpapers/sql-injection.jpg /opt/seclab-wallpapers/default.jpg

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    nmap \
    netcat-openbsd \
    tcpdump \
    firefox-esr \
    curl \
    wget \
    dirb \
    sqlmap \
    hydra \
    dnsutils \
    whois \
    traceroute \
    net-tools \
    iputils-ping \
    openssh-client \
    sshpass \
    socat \
    gobuster \
    ffuf \
    wfuzz \
    python3-pip \
    python3-dev \
    git \
    vim \
    gdb \
    gdbserver \
    build-essential \
    file \
    ltrace \
    strace && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    requests pwntools

# pwndbg（GDB 插件，用于栈溢出等二进制实验）：克隆并安装，setup.sh 会自动配置 ~/.gdbinit，
# 兜底再显式 source 一次，保证学生直接 `gdb pwn` 即可加载 pwndbg。
RUN DEBIAN_FRONTEND=noninteractive git clone --depth 1 https://github.com/pwndbg/pwndbg /opt/pwndbg && \
    cd /opt/pwndbg && \
    ./setup.sh && \
    ( grep -q pwndbg /root/.gdbinit 2>/dev/null || echo "source /opt/pwndbg/gdbinit.py" >> /root/.gdbinit ) && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 关闭 pwndbg 启动时的自动更新（避免每次启动 gdb 都联网、在离线/内网环境卡顿或失败）
ENV PWNDBG_NO_AUTOUPDATE=1

ENTRYPOINT ["supervisord", "-n"]
