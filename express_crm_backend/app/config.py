import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Express Platform Backend API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database (Default SQLite for instant portability, or PostgreSQL URL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./express_platform.db"
    )
    
    # JWT Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_key_2026_express_platform_key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # Default Category Commission Rate
    DEFAULT_COMMISSION_RATE: float = 2.00  # 2% standard
    
    # Media / Storage
    BASE_MEDIA_URL: str = "http://localhost:5000/media"
    
    # Agora Voice / Video & Chat Config
    AGORA_APP_ID: str = os.getenv("AGORA_APP_ID", "1f0289c692b4450fba150fafd95cd489")
    AGORA_TEMP_TOKEN: str = os.getenv("AGORA_TEMP_TOKEN", "007eJxTYHiVaLSzTvLL3L8/VlqxiYk/VJxn5eGSkrbHe+U+k/vmwrkKDIZpBkYWlslmlkZJJiamBmlJiYZAMjEtxdI0OcXEwpJnw7ashkBGhqsCp1kZGSAQxGdnSK0oKEotLmZgAAB7PSAj")
    AGORA_APP_CERTIFICATE: str = os.getenv("AGORA_APP_CERTIFICATE", "")
    AGORA_CHAT_WS_URL: str = os.getenv("AGORA_CHAT_WS_URL", "msync-api-61.chat.agora.io")
    AGORA_CHAT_REST_URL: str = os.getenv("AGORA_CHAT_REST_URL", "a61.chat.agora.io")

    class Config:

        env_file = ".env"
        extra = "allow"

settings = Settings()
