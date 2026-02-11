FROM ruby:3.4.8-slim AS build

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

WORKDIR /app

COPY Gemfile Gemfile.lock ./
RUN bundle install \
	&& rm -rf /usr/local/bundle/cache \
	&& find /usr/local/bundle -name "*.c" -delete \
	&& find /usr/local/bundle -name "*.o" -delete

COPY . .

RUN --mount=type=secret,id=rails_master_key \
	/bin/sh -c "RAILS_MASTER_KEY=$(cat /run/secrets/rails_master_key) bundle exec rails assets:precompile"

FROM ruby:3.4.8-slim

ENV BUNDLE_PATH=/usr/local/bundle \
		BUNDLE_WITHOUT=development:test \
		RAILS_ENV=production

RUN apt-get update -qq \
	&& apt-get install -y --no-install-recommends \
		libmariadb3 \
		libyaml-0-2 \
		curl \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=build /usr/local/bundle /usr/local/bundle
COPY --from=build /app /app

RUN groupadd --system rails && useradd --system --gid rails --create-home rails \
	&& chown -R rails:rails /app

USER rails

EXPOSE 3000

CMD ["bash", "-lc", "rm -f tmp/pids/server.pid && bundle exec rails server -b 0.0.0.0 -p 3000"]
