FROM ubuntu:22.04@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401
RUN apt-get update && apt-get install -y --no-install-recommends libcurl4 libssl3 ca-certificates python3 python3-venv && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake python3-dev zlib1g-dev liblz4-dev && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/reader && /opt/reader/bin/pip install --no-cache-dir amulet-leveldb amulet-nbt
COPY bds-1.26.52.3/ /opt/bds/
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/bds/bedrock_server /opt/entrypoint.sh
WORKDIR /srv/bds
ENV LD_LIBRARY_PATH=/srv/bds
ENTRYPOINT ["/opt/entrypoint.sh"]
