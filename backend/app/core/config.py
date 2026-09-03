"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -------------------------------------------------------------------------
    # MongoDB
    # -------------------------------------------------------------------------
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "revenue_recovery"

    # -------------------------------------------------------------------------
    # Razorpay
    # -------------------------------------------------------------------------
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # -------------------------------------------------------------------------
    # LiveKit
    # -------------------------------------------------------------------------
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    # -------------------------------------------------------------------------
    # Google Gemini
    # -------------------------------------------------------------------------
    GOOGLE_API_KEY: str

    # -------------------------------------------------------------------------
    # Deepgram
    # -------------------------------------------------------------------------
    DEEPGRAM_API_KEY: str

    # -------------------------------------------------------------------------
    # ElevenLabs
    # -------------------------------------------------------------------------
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str

    # -------------------------------------------------------------------------
    # Recovery Policy
    # -------------------------------------------------------------------------
    MAX_CALL_ATTEMPTS: int = 2
    MAX_PAYMENT_LINKS: int = 2
    MAX_REMINDERS: int = 2
    MAX_RECOVERY_DAYS: int = 7

    AUTO_RECOVERY_LIMIT: float = 5000
    HIGH_VALUE_THRESHOLD: float = 25000

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    # -------------------------------------------------------------------------
    # Pydantic Settings
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()