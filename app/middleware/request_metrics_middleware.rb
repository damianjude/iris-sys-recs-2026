class RequestMetricsMiddleware
  METRICS_PATH = "/metrics".freeze

  def initialize(app)
    @app = app
  end

  def call(env)
    request = ActionDispatch::Request.new(env)
    return @app.call(env) if request.path == METRICS_PATH

    started_at = Process.clock_gettime(Process::CLOCK_MONOTONIC)
    status, headers, response = @app.call(env)
    duration = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started_at

    endpoint = endpoint_label(env, request)
    labels = {
      method: request.request_method,
      endpoint: endpoint,
      status: status.to_s
    }

    IrisMetrics.http_requests_total.increment(labels: labels)
    IrisMetrics.http_request_duration_seconds.observe(duration, labels: labels)
    IrisMetrics.http_request_errors_total.increment(labels: labels) if status >= 500

    [status, headers, response]
  end

  private

  def endpoint_label(env, request)
    params = env["action_dispatch.request.path_parameters"]
    return request.path if params.blank?

    controller = params[:controller]
    action = params[:action]
    return request.path if controller.blank? || action.blank?

    "#{controller}##{action}"
  end
end