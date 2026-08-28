from __future__ import annotations

import os

os.environ.setdefault("BITRIXVM_ENVIRONMENT", "test")
os.environ.setdefault("BITRIXVM_MASTER_KEY", "test-master-key-material-at-least-32-bytes")
os.environ.setdefault("BITRIXVM_JWT_SECRET", "test-jwt-secret-material-at-least-32-bytes")
os.environ.setdefault("BITRIXVM_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
