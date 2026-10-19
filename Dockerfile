# Nové bydlení: hlídání nabídek pronájmu na realitních portálech + webová stránka
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src CONFIG_FILE=/config/hledani.yaml DATA_DIR=/data PORT=8080

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config/hledani.yaml /config/hledani.yaml

RUN useradd --system --uid 10001 --home /data app && mkdir -p /data && chown app /data
USER 10001
VOLUME ["/data"]
EXPOSE 8080
CMD ["python", "-m", "nove_bydleni"]
