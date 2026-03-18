from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # JWT
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8888/auth/google/callback"

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Social Event Mapper"

    # App
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8888"
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
