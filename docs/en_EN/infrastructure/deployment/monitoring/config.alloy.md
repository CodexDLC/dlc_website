# 📜 Grafana Agent Configuration (`config.alloy`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This `config.alloy` file defines the configuration for Grafana Agent (using the Alloy language) to collect and forward logs to Loki and metrics to Prometheus (Grafana Cloud). It's designed to monitor Docker containers and the host system.

## Constants

```alloy
constants {
  hostname = "lily-salon-vps"
  project_name = sys.env("COMPOSE_PROJECT_NAME")
}
```
*   `hostname`: Sets a static hostname label for all collected data.
*   `project_name`: Dynamically retrieves the Docker Compose project name from environment variables.

## Logs (Loki)

### `discovery.docker "linux_containers"`

```alloy
discovery.docker "linux_containers" {
  host = "unix:///var/run/docker.sock"
  refresh_interval = "15s"
}
```
Discovers running Docker containers on the host by connecting to the Docker socket.
*   `host`: Specifies the Docker socket path.
*   `refresh_interval`: How often to refresh the list of containers.

### `loki.source.docker "docker_logs"`

```alloy
loki.source.docker "docker_logs" {
  nodes = discovery.docker.linux_containers.targets
  client = loki.write.grafana_loki.receiver

  forward_to = [loki.write.grafana_loki.receiver]
}
```
Collects logs from the discovered Docker containers.
*   `nodes`: Uses the targets discovered by `discovery.docker.linux_containers`.
*   `client`: Specifies the Loki writer to use.
*   `forward_to`: Forwards collected logs to the `grafana_loki` writer.

### `loki.write "grafana_loki"`

```alloy
loki.write "grafana_loki" {
  endpoint {
    url = sys.env("GCLOUD_HOSTED_LOGS_URL")
    basic_auth {
      username = sys.env("GCLOUD_HOSTED_LOGS_ID")
      password = sys.env("GCLOUD_RW_API_KEY")
    }
  }
}
```
Configures the Loki client to write logs to Grafana Cloud.
*   `url`: Retrieves the Loki endpoint URL from `GCLOUD_HOSTED_LOGS_URL` environment variable.
*   `basic_auth`: Uses basic authentication with credentials from `GCLOUD_HOSTED_LOGS_ID` and `GCLOUD_RW_API_KEY` environment variables.

## Metrics (Prometheus)

### `prometheus.exporter.unix "node_exporter"`

```alloy
prometheus.exporter.unix "node_exporter" { }
```
Enables the Unix node exporter, which collects system-level metrics (CPU, memory, disk, network) from the host.

### `prometheus.scrape "node_metrics"`

```alloy
prometheus.scrape "node_metrics" {
  targets    = prometheus.exporter.unix.node_exporter.targets
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
}
```
Scrapes metrics from the `node_exporter`.
*   `targets`: Uses the targets provided by `prometheus.exporter.unix.node_exporter`.
*   `forward_to`: Forwards collected metrics to the `grafana_cloud` remote writer.

### `prometheus.remote_write "grafana_cloud"`

```alloy
prometheus.remote_write "grafana_cloud" {
  endpoint {
    url = sys.env("GCLOUD_HOSTED_METRICS_URL")
    basic_auth {
      username = sys.env("GCLOUD_HOSTED_METRICS_ID")
      password = sys.env("GCLOUD_RW_API_KEY")
    }
  }
}
```
Configures the Prometheus remote writer to send metrics to Grafana Cloud.
*   `url`: Retrieves the Prometheus endpoint URL from `GCLOUD_HOSTED_METRICS_URL` environment variable.
*   `basic_auth`: Uses basic authentication with credentials from `GCLOUD_HOSTED_METRICS_ID` and `GCLOUD_RW_API_KEY` environment variables.
