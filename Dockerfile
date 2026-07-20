FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip wheel --wheel-dir /build/wheels -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/app/data/playwright

RUN groupadd --system alduor \
    && useradd --system --gid alduor --create-home --home-dir /home/alduor alduor

WORKDIR /app
COPY --from=builder /build/wheels /wheels
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY . .
RUN mkdir -p /app/data/database /app/data/exports /app/data/backups /app/data/logs /app/data/playwright \
    && chown -R alduor:alduor /app

# The dynamic-render fallback (playwright_renderer.py) needs an actual browser binary,
# not just the `playwright` python package - without this, every JS-heavy site falls
# through to a "Playwright fallback failed: Executable doesn't exist" warning and the
# static-only crawl is all you get. --with-deps also pulls the OS-level shared libs
# Chromium needs, which python:3.12-slim doesn't ship with.
RUN playwright install --with-deps chromium

USER alduor
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
