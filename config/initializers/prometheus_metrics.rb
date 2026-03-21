module IrisMetrics
  module_function

  def registry
    Prometheus::Client.registry
  end

  def fetch_or_register(name)
    yield
  rescue Prometheus::Client::Registry::AlreadyRegisteredError
    registry.get(name)
  end

  def app_up
    @app_up ||= fetch_or_register(:rails_app_up) do
      registry.gauge(:rails_app_up, docstring: "Rails app availability")
    end
  end

  def http_requests_total
    @http_requests_total ||= fetch_or_register(:rails_http_requests_total) do
      registry.counter(
        :rails_http_requests_total,
        docstring: "Total HTTP requests handled by Rails",
        labels: %i[method endpoint status]
      )
    end
  end

  def http_request_errors_total
    @http_request_errors_total ||= fetch_or_register(:rails_http_request_errors_total) do
      registry.counter(
        :rails_http_request_errors_total,
        docstring: "Total HTTP 5xx responses handled by Rails",
        labels: %i[method endpoint status]
      )
    end
  end

  def http_request_duration_seconds
    @http_request_duration_seconds ||= fetch_or_register(:rails_http_request_duration_seconds) do
      registry.histogram(
        :rails_http_request_duration_seconds,
        docstring: "HTTP request latency in seconds",
        labels: %i[method endpoint status],
        buckets: [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5]
      )
    end
  end
end

IrisMetrics.app_up.set(1)