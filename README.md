# iris-sys-recs-2026

## Running the project

To run the project, ensure you have Docker and Rails installed on your machine. Then, clone this repository and execute the following commands:

1. To set up the Rails credentials, run:

```bash
rm -f config/credentials.yml.enc config/master.key && rails credentials:edit
```

2. To build and start the application along with all its services, run:

```bash
docker compose up --build
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

## Implementation details

### Dockerfile
The Dockerfile uses a multi-stage build to optimize the final image size. The first stage uses the official Ruby image to install dependencies and build the application, while the second stage uses a lightweight Alpine image to run the application. It also uses a non-root user to enhance security. The application is configured to run in production mode. It also uses an entrypoint script to read the master key from the environment variable set by docker-compose, which in turn reads the value from `./config/` (hence the command to set up credentials in the instructions above). The entrypoint script also ensures that the rails app is set up with PID 1, allowing it to receive SIGTERM signals properly for graceful shutdowns.

### Docker Compose
The `docker-compose.yml` file defines the services for the Rails application, NGINX, MySQL database, Prometheus, Grafana, and the backup container. It sets up the necessary environment variables, volumes, and network configurations for each service. The Rails application is configured to connect to the MySQL database using environment variables for the database host, username, password, and name. NGINX is set up to listen on port 80 and forward requests to the Rails application containers. Prometheus is configured to scrape metrics from the specified exporters, and Grafana is set up with a provisioned dashboard for monitoring.

### nginx and Load Balancing

nginx is configured to load balance incoming requests across the three Rails application containers using `least_conn` load balancing method, which directs traffic to the server with the least number of active connections. A rate limit has also been implemented to allow a maximum of 10 requests per second with a burst of 20 requests, and any requests exceeding this limit will receive a 429 status code.

### Persistence

The MySQL database uses a Docker volume (`db_data`) to ensure data persistence across container restarts. The DB used is the production database. NGINX, Prometheus, and Grafana configuration files are mounted from the repository, making the setup reproducible. The backup container uses a bind mount to the host's `/backups` directory to store the generated backups, ensuring they are accessible even if the container is recreated. Prometheus data is also stored in a Docker volume (`prometheus_data`) to ensure that metrics data is retained across container restarts. The app data is stored in a Docker volume (`storage_data`) to ensure that any uploaded files are persisted across containers (even though they are load balanced) and container restarts.

### Monitoring

Prometheus is configured to scrape metrics from the `cAdvisor`, `mysqld-exporter`, and `nginx-prometheus-exporter` exporter. Grafana is set up with a provisioned dashboard to visualize these metrics, allowing you to monitor the performance and health of the application and its components effectively. The dashboard includes panels for monitoring the number of requests, response times, database performance, and resource usage of the containers.

### Backup

A python backup script acting as a daemon periodically creates backups of the MySQL database and the application code, storing them in the `/backups` directory on the host. For the backups, it compares the SHA256 hash of the new backup with existing ones and only keeps it if it's different, ensuring that only unique backups are retained. The code backup is compressed using `tar.xz` compression. The backup container is configured to run every hour (3600 seconds) and retains backups for 30 days, automatically deleting older backups. It mounts the application code as a read-only volume to ensure that the backup process does not interfere with the running application.

### GitHub Actions

A GitHub Actions workflow is set up to publish the app's docker image to Docker Hub at `vidowal449/iris-sys-recs-2026`, whenever a new release is created. It also caches the Docker layers to speed up the build process for subsequent releases.