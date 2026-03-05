FROM ubuntu:questing

ENV DEBIAN_FRONTEND=noninteractive

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# hadolint ignore=DL3016
WORKDIR /
COPY --chown=circleci:circleci bin bin

# hadolint ignore=DL3059,DL3013
RUN pip3 install --no-cache-dir -U wpls
CMD ["wpls", "-h"]
