import os

os.environ.setdefault("BUILD_TIME", "1")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("DEBUG", "true")
