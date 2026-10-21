FROM nginxinc/nginx-unprivileged:1.30.4-alpine3.24

COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=101:101 index.html /usr/share/nginx/html/index.html

EXPOSE 8080
