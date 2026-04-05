import os

# Must be set before Django is imported so IS_BUILD=True in settings,
# which switches the DB to SQLite and skips loading JWT key files from disk.
os.environ["BUILD_TIME"] = "1"
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("DEBUG", "true")
