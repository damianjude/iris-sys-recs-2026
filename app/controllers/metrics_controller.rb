class MetricsController < ActionController::Base
  def show
    IrisMetrics.app_up.set(1)
    body = render_metrics(Prometheus::Client.registry.metrics)

    render plain: body, content_type: "text/plain; version=0.0.4; charset=utf-8"
  end

  private

  def render_metrics(metrics)
    lines = []

    metrics.each do |metric|
      metric_name = metric.name.to_s
      metric_type = metric.class.name.split("::").last.downcase
      lines << "# HELP #{metric_name} #{escape_help(metric.docstring)}"
      lines << "# TYPE #{metric_name} #{metric_type}"

      metric.values.each do |labels, value|
        if metric_type == "histogram"
          lines.concat(histogram_lines(metric_name, labels, value))
        else
          lines << "#{metric_name}#{format_labels(labels)} #{value}"
        end
      end
    end

    lines.join("\n") + "\n"
  end

  def histogram_lines(metric_name, labels, buckets)
    label_hash = labels.dup
    lines = []

    buckets.each do |bucket, bucket_value|
      next if bucket == "sum"

      lines << "#{metric_name}_bucket#{format_labels(label_hash.merge(le: bucket))} #{bucket_value}"
    end

    lines << "#{metric_name}_sum#{format_labels(label_hash)} #{buckets["sum"]}"
    lines << "#{metric_name}_count#{format_labels(label_hash)} #{buckets.fetch("+Inf", 0)}"
    lines
  end

  def format_labels(labels)
    return "" if labels.blank?

    encoded = labels.map do |key, value|
      %(#{key}="#{escape_label(value)}")
    end

    "{#{encoded.join(",")}}"
  end

  def escape_help(text)
    text.to_s.gsub("\\", "\\\\").gsub("\n", "\\n")
  end

  def escape_label(value)
    value.to_s.gsub("\\", "\\\\").gsub("\n", "\\n").gsub('"', '\\"')
  end
end