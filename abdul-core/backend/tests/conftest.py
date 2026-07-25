"""Pytest configuration for Abdul Core."""

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://abdul:abdul@localhost:5432/abdul_core")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://abdul:abdul@localhost:5432/abdul_core")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("PORTFOLIO_API_KEY", "test-portfolio-key")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "placeholder")

