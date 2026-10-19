# Nové bydlení: hlídání nabídek pronájmu na realitních portálech + webová stránka
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src CONFIG_FILE=/config/hledani.yaml DATA_DIR=/data PORT=8080

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config/hledani.yaml /config/hledani.yaml

# uid mimo 10000–19999: na ITX je k cgroupám připojený androidí filtr socketů (uid_permission_map), ten by aplikaci zakázal síť
RUN useradd --system --uid 65532 --home /data app && mkdir -p /data && chown app /data
USER 65532
VOLUME ["/data"]
EXPOSE 8080
CMD ["python", "-m", "nove_bydleni"]
