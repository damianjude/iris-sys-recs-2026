FROM ruby:3.4.8-slim

ENV BUNDLE_PATH=/usr/local/bundle \
		BUNDLE_WITHOUT=development:test

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
RUN bundle install

COPY . .

EXPOSE 3000

CMD ["bash", "-lc", "rm -f tmp/pids/server.pid && bundle exec rails server -b 0.0.0.0 -p 3000"]
