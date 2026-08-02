FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY plugins ./plugins

RUN groupadd --gid 10001 viralai \
    && useradd --uid 10001 --gid viralai --create-home --shell /usr/sbin/nologin viralai \
    && mkdir -p /var/lib/viralai \
    && chown -R viralai:viralai /app /var/lib/viralai

USER viralai

EXPOSE 8000

CMD ["uvicorn", "viralai.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
