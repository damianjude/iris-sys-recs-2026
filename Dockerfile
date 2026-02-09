FROM ruby:3.4.8-slim

ENV BUNDLE_PATH=/usr/local/bundle \
		BUNDLE_WITHOUT=development:test \
		RAILS_ENV=production

RUN apt-get update -qq \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		default-libmysqlclient-dev \
		libyaml-dev \
		pkg-config \
		git \
		curl \
	&& rm -rf /var/lib/apt/lists/*

RUN groupadd --system rails && useradd --system --gid rails --create-home rails

WORKDIR /app

COPY Gemfile Gemfile.lock ./
RUN bundle install

COPY . .

RUN --mount=type=secret,id=rails_master_key \
	/bin/sh -c "RAILS_MASTER_KEY=$(cat /run/secrets/rails_master_key) bundle exec rails assets:precompile"

RUN chown -R rails:rails /app

USER rails

EXPOSE 3000

CMD ["bash", "-lc", "rm -f tmp/pids/server.pid && bundle exec rails server -b 0.0.0.0 -p 3000"]
