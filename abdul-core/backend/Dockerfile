FROM python:3.12-slim AS builder

WORKDIR /app
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY pyproject.toml .
COPY . .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir ".[dev]"

FROM python:3.12-slim AS runtime

ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
RUN adduser --disabled-password --gecos "" abdul
COPY --from=builder /venv /venv
COPY . .
USER abdul
EXPOSE 8000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]

