FROM php:7.3-fpm-alpine

COPY conf /tmp/
COPY files /var/www/html


# 安装必要的软件包
RUN apk add --update --no-cache tar nginx bash \
    #&& mkdir /run/nginx \
    # configure file
    && mv /tmp/flag.sh /flag.sh \
    && mv /tmp/flag /flag \
    && mv /tmp/seclab-command-hook.sh /usr/local/bin/seclab-command-hook.sh \
    && mv /tmp/docker-entrypoint /usr/local/bin/docker-entrypoint \
    && chmod +x /usr/local/bin/docker-entrypoint \
    && chmod +x /usr/local/bin/seclab-command-hook.sh \
    && printf '%s\n' 'if [ -n "$BASH_VERSION" ] && [ "${SECLAB_COMMAND_HOOK_ENABLED:-true}" != "false" ]; then . /usr/local/bin/seclab-command-hook.sh; fi' > /etc/profile.d/seclab-command-hook.sh \
    && printf '%s\n' 'if [ -n "$BASH_VERSION" ] && [ -f /usr/local/bin/seclab-command-hook.sh ] && [ "${SECLAB_COMMAND_HOOK_ENABLED:-true}" != "false" ]; then . /usr/local/bin/seclab-command-hook.sh; fi' >> /root/.bashrc \
    && if [ -f /etc/bash/bashrc ]; then printf '%s\n' 'if [ -n "$BASH_VERSION" ] && [ -f /usr/local/bin/seclab-command-hook.sh ] && [ "${SECLAB_COMMAND_HOOK_ENABLED:-true}" != "false" ]; then . /usr/local/bin/seclab-command-hook.sh; fi' >> /etc/bash/bashrc; fi \
    && mv /tmp/nginx.conf /etc/nginx/nginx.conf \
    && chown -R www-data:www-data /var/www/html \
    # clear
    && rm -rf /tmp/*

WORKDIR /var/www/html

EXPOSE 80

ENTRYPOINT ["docker-entrypoint"]
