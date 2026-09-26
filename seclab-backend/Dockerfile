FROM php:7.4-apache

# 安装 mysqli 扩展
RUN docker-php-ext-install mysqli

# 拷贝 web 页面
COPY ./web/ /var/www/html/

# 设置权限
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

EXPOSE 80

CMD ["apache2-foreground"]
