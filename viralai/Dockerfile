FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRALAI_ENVIRONMENT=production \
    VIRALAI_DATA_DIR=/var/lib/viralai \
    VIRALAI_PLUGINS_DIR=/app/plugins

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir .

RUN mkdir -p /var/lib/viralai /app/plugins \
    && groupadd --gid 10001 viralai \
    && useradd --uid 10001 --gid viralai --create-home --shell /usr/sbin/nologin viralai \
    && chown -R viralai:viralai /app /var/lib/viralai

USER viralai

EXPOSE 8000

ENTRYPOINT ["viralai"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
