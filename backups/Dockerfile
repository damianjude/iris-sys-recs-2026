FROM python:3.14.3-alpine3.23

WORKDIR /backup

COPY . .

RUN apk add --no-cache \
    mysql-client mariadb-connector-c

CMD ["python", "backups/backup.py"]