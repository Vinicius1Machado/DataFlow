import os


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("MINIO_ROOT_USER", "test_minio_user")
os.environ.setdefault("MINIO_ROOT_PASSWORD", "test_minio_password")
os.environ.setdefault("N8N_BASIC_AUTH_USER", "test_n8n_user")
os.environ.setdefault("N8N_BASIC_AUTH_PASSWORD", "test_n8n_password")
os.environ.setdefault("N8N_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
