import os


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/schedule.db")
DEFAULT_BUDGET = float(os.getenv("DEFAULT_BUDGET", "100.0"))
EXCHANGE_RATE_USD_TO_CNY = float(os.getenv("EXCHANGE_RATE_USD_TO_CNY", "7.25"))
