FROM postgres:16-alpine

RUN apk add --no-cache dcron tzdata bash gzip

ENV TZ=Asia/Almaty

COPY backup.sh /usr/local/bin/backup.sh
COPY restore.sh /usr/local/bin/restore.sh
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /usr/local/bin/backup.sh /usr/local/bin/restore.sh /entrypoint.sh

# Cron: backup every day at 03:00 + cleanup old (keep last 30 days)
RUN echo "0 3 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root

VOLUME ["/backups"]

ENTRYPOINT ["/entrypoint.sh"]
