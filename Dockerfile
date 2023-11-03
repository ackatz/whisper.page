FROM python:slim as builder

RUN apt-get update && apt-get install -y wget curl --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN SUPERCRONIC_RELEASE=$(curl -I https://github.com/aptible/supercronic/releases/latest | awk -F '/' '/^location/ {print  substr($NF, 1, length($NF)-1)}' | sed 's/%0D//g') \
    && wget https://github.com/aptible/supercronic/releases/download/$SUPERCRONIC_RELEASE/supercronic-linux-amd64 -O /usr/local/bin/supercronic && chmod +x "/usr/local/bin/supercronic"

COPY . /app


FROM python:slim

COPY --from=flyio/litefs:0.5 /usr/local/bin/litefs /usr/local/bin/litefs
COPY --from=builder /usr/local/bin/supercronic /usr/local/bin/supercronic
COPY --from=builder /app /app
COPY . /app
COPY litefs.yml /etc/litefs.yml

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:${PYTHONPATH}"

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN apt update && apt install -y python3-dev supervisor ca-certificates fuse3 sqlite3 pkg-config ca-certificates build-essential libssl-dev libffi-dev --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade wheel setuptools pip
RUN pip install --upgrade -r /app/requirements/app.txt
RUN pip install --pre pendulum

RUN mkdir /app/log

EXPOSE 8000

ENTRYPOINT litefs mount