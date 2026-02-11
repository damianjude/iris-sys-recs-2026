FROM python:3.14.3-alpine3.23

WORKDIR /backups

COPY backup.py .

RUN apk add --no-cache \
    mysql-client mariadb-connector-c

CMD ["python", "backup.py"]