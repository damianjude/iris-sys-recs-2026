# iris-sys-recs-2026

## Running the project

To run the project, ensure you have Docker and Docker Compose installed on your machine. Then, navigate to the project directory and execute the following command:

```bash
docker-compose up --build
```

The app will be accessible at `http://localhost` and Grafana will be accessible at `http://localhost:3001` with the default credentials (admin/admin).

## Overview

This project has implemented all tasks specified, including the bonus tasks:

- Three dockerised Rails application containers
- NGINX serving as a reverse proxy to the Rails applications
- MySQL database container
- Grafana for monitoring with a pre-configured dashboard
- Prometheus for metrics collection from the cAdvisor, mysqld-exporter, and the nginx exporter
- GitHub Actions workflow to publish the app's docker image to Docker Hub at `vidowal449/iris-sys-recs-2026` whenever a new release is created
- A backup container that periodically creates backups of the MySQL database and the application code, storing them in a bind mounted volume `/backups` on the host

## Load Balancing

NGINX is configured to load balance incoming requests across the three Rails application containers using `least_conn` load balancing method, which directs traffic to the server with the least number of active connections.

## Persistence

The MySQL database uses a Docker volume (`db_data`) to ensure data persistence across container restarts. NGINX, Prometheus, and Grafana configuration files are mounted from the repository, making the setup reproducible. The backup container uses a bind mount to the host's `/backups` directory to store the generated backups, ensuring they are accessible even if the container is recreated.

## Monitoring

Prometheus is configured to scrape metrics from the `cAdvisor`, `mysqld-exporter`, and `nginx-prometheus-exporter` exporter. Grafana is set up with a provisioned dashboard to visualize these metrics, allowing you to monitor the performance and health of the application and its components effectively.

## Backup

A python backup script acting as a daemon periodically creates backups of the MySQL database and the application code, storing them in the `/backups` directory on the host. For the databases, it compares the SHA256 hash of the new backup with existing ones and only keeps it if it's different, ensuring that only unique backups are retained. For the application code, it creates a tarball (xz compressed) of the relevant directories in the allowlist.

## GitHub Actions

A GitHub Actions workflow is set up to publish the app's docker image to Docker Hub at `vidowal449/iris-sys-recs-2026`, whenever a new release is created.
