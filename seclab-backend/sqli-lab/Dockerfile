FROM php:7.4-apache

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libzip-dev \
    zip \
    && rm -rf /var/lib/apt/lists/*

# 安装 PHP 扩展
RUN docker-php-ext-install mysqli pdo pdo_mysql zip

# 配置Apache默认文档 (index.php 优先，避免 index.html 乱码问题)
RUN sed -i 's/DirectoryIndex.*/DirectoryIndex index.php index.html/' /etc/apache2/mods-available/dir.conf

# 设置 PHP 默认编码为 UTF-8
RUN echo 'default_charset = "UTF-8"' >> /usr/local/etc/php/conf.d/charset.ini

# 拷贝 web 页面
COPY ./web/ /var/www/html/

# 设置权限
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

EXPOSE 80

CMD ["apache2-foreground"]
