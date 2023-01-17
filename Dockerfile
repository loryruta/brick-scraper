FROM debian:latest

RUN apt-get update
RUN apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    cron

COPY . /usr/app/

WORKDIR /usr/app/

RUN pip install -r requirements.txt && \
    npm install

RUN crontab -l | { cat; echo "*/10 * * * * python3 /usr/app/src/pull_catalog.py"; } | crontab -
RUN crontab -l | { cat; echo "*/10 * * * * python3 /usr/app/src/pull_inventory_images.py"; } | crontab -
RUN crontab -l | { cat; echo "*/10 * * * * python3 /usr/app/src/pull_orders.py"; } | crontab -

ENTRYPOINT alembic upgrade head && \
    python3 main.py
