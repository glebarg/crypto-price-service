import os

# Keep test collection independent of a local PostgreSQL installation.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
