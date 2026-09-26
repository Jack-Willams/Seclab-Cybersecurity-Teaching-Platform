FROM php:7.4-apache

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libzip-dev \
    zip \
    && rm -rf /var/lib/apt/lists/*

# 安装 PHP 扩展
RUN docker-php-ext-install mysqli pdo pdo_mysql zip

# 配置Apache默认文档
RUN sed -i 's/DirectoryIndex.*/DirectoryIndex index.html index.php/' /etc/apache2/mods-available/dir.conf

# 拷贝 web 页面
COPY ./web/ /var/www/html/

# 创建文件目录
RUN mkdir -p /var/www/html/files \
    && chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html \
    && chmod 755 /var/www/html/files

EXPOSE 80

CMD ["apache2-foreground"] 