FROM nginxinc/nginx-unprivileged:1.30.4-alpine3.24

USER root
RUN apk upgrade --no-cache

COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=101:101 index.html /usr/share/nginx/html/index.html

USER 101
EXPOSE 8080