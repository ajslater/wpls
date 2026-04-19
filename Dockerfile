# hadolint ignore=DL3007
FROM nikolaik/python-nodejs:python3.14-nodejs24
ENV DEBIAN_FRONTEND=noninteractive

COPY debian.sources /etc/apt/sources.list.d/
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY bin bin
# hadolint ignore=DL3059

COPY pyproject.toml uv.lock package.json package-lock.json ./
RUN npm install

COPY . .
RUN mkdir -p test-results dist

# Install
# hadolint ignore=DL3059
RUN uv sync