"""
Application configuration using pydantic-settings.
Reads from .env file automatically.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="revenue_recovery")

    # Razorpay
    RAZORPAY_KEY_ID: str = Field(default="")
    RAZORPAY_KEY_SECRET: str = Field(default="")
    RAZORPAY_WEBHOOK_SECRET: str = Field(default="")

    # LiveKit
    LIVEKIT_URL: str = Field(default="")
    LIVEKIT_API_KEY: str = Field(default="")
    LIVEKIT_API_SECRET: str = Field(default="")

    # Google Gemini
    GOOGLE_API_KEY: str = Field(default="")

    # Deepgram STT
    DEEPGRAM_API_KEY: str = Field(default="")

    # ElevenLabs TTS
    ELEVENLABS_API_KEY: str = Field(default="")
    ELEVENLABS_VOICE_ID: str = Field(default="EXAVITQu4vr4xnSDxMaL")

    # Recovery Policy Thresholds
    MAX_CALL_ATTEMPTS: int = Field(default=2)
    MAX_PAYMENT_LINKS: int = Field(default=2)
    MAX_REMINDERS: int = Field(default=2)
    MAX_RECOVERY_DAYS: int = Field(default=7)
    AUTO_RECOVERY_LIMIT: float = Field(default=5000.0)   # INR
    HIGH_VALUE_THRESHOLD: float = Field(default=25000.0)  # INR

    # App
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    ENVIRONMENT: str = Field(default="development")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
