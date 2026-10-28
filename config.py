import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    # Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "crimevision-ai-forensic-secret-key-2026")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'crimevision.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Storage Paths
    STORAGE_DIR = BASE_DIR / "storage"
    ORIGINALS_DIR = STORAGE_DIR / "originals"
    PROCESSED_DIR = STORAGE_DIR / "processed"
    REPORTS_DIR = STORAGE_DIR / "reports"
    DEMO_DIR = STORAGE_DIR / "demo"

    # Upload constraints
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "500")) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a"}
    ALLOWED_EXTENSIONS = (
        ALLOWED_IMAGE_EXTENSIONS
        | ALLOWED_VIDEO_EXTENSIONS
        | ALLOWED_AUDIO_EXTENSIONS
    )

    # AI & ML settings
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    RT_DETR_MODEL_PATH = os.getenv("RT_DETR_MODEL_PATH", "rtdetr-l.pt")
    CUSTOM_WEAPON_MODEL_PATH = os.getenv("CUSTOM_WEAPON_MODEL_PATH", "")
    CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
    BLIP_MODEL_NAME = os.getenv("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-base")
    WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "base")
    VIDEO_SAMPLE_FPS = float(os.getenv("VIDEO_SAMPLE_FPS", "1.0"))
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))

    # Demo mode
    ENABLE_DEMO_MODE = os.getenv("ENABLE_DEMO_MODE", "false").lower() in ("true", "1", "yes")

    @classmethod
    def init_app(cls, app):
        """Ensure all storage directories exist."""
        for path in [cls.ORIGINALS_DIR, cls.PROCESSED_DIR, cls.REPORTS_DIR, cls.DEMO_DIR]:
            path.mkdir(parents=True, exist_ok=True)
