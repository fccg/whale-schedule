import os


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/schedule.db")
DEFAULT_BUDGET = float(os.getenv("DEFAULT_BUDGET", "100.0"))
EXCHANGE_RATE_USD_TO_CNY = float(os.getenv("EXCHANGE_RATE_USD_TO_CNY", "7.25"))

# Primary provider selection
PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "autodl")

# AutoDL provider settings
AUTODL_API_BASE = os.getenv("AUTODL_API_BASE", "https://api.autodl.com")
AUTODL_API_KEY = os.getenv("AUTODL_API_KEY", "")
AUTODL_DEFAULT_IMAGE_UUID = os.getenv("AUTODL_DEFAULT_IMAGE_UUID", "")
AUTODL_DEFAULT_CUDA_V_FROM = int(os.getenv("AUTODL_DEFAULT_CUDA_V_FROM", "113"))
AUTODL_DEFAULT_GPU_AMOUNT = int(os.getenv("AUTODL_DEFAULT_GPU_AMOUNT", "1"))
AUTODL_DEFAULT_SYSTEM_DISK_GB = int(os.getenv("AUTODL_DEFAULT_SYSTEM_DISK_GB", "0"))
AUTODL_DATA_CENTER_LIST = os.getenv("AUTODL_DATA_CENTER_LIST", "")

# Allowed CORS origins
ALLOW_ORIGINS = os.getenv("CORS_ORIGIN", "http://localhost:3000,http://localhost:18761,http://115.191.43.252:18761")
