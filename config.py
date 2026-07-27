"""
config.py – Konfigurasi aplikasi Flask
"""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Konfigurasi utama aplikasi Flask."""

    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Mode debug (matikan di production)
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"

    # ── Path model ──────────────────────────────────────────────────────────
    MODEL_PATH         = os.path.join(BASE_DIR, "src", "model", "model_production.pkl")
    ENCODERS_PATH      = os.path.join(BASE_DIR, "src", "model", "encoders.pkl")
    FEATURE_LIST_PATH  = os.path.join(BASE_DIR, "src", "model", "feature_list.json")

    # ── Path data ────────────────────────────────────────────────────────────
    ISHIHARA_DIR       = os.path.join(BASE_DIR, "src", "img", "ishihara")
    QUESTIONS_PATH     = os.path.join(BASE_DIR, "src", "data", "questions.txt")

    # ── Upload ───────────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
