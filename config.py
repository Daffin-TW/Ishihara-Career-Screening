"""
config.py – Konfigurasi aplikasi Flask
"""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Konfigurasi utama aplikasi Flask."""
    BASE_DIR = BASE_DIR

    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Mode debug (matikan di production)
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"

    # ── Path model ──────────────────────────────────────────────────────────
    MODEL_PATH         = os.path.join(BASE_DIR, "src", "model", "model_production.pkl")
    ENCODERS_PATH      = os.path.join(BASE_DIR, "src", "model", "encoders.pkl")
    FEATURE_LIST_PATH  = os.path.join(BASE_DIR, "src", "model", "feature_list.json")

    # ── Path data ────────────────────────────────────────────────────────────
    _src_ishihara = os.path.join(BASE_DIR, "src", "img", "ishihara")
    _root_ishihara = os.path.join(BASE_DIR, "ishihara")
    ISHIHARA_DIR = _src_ishihara if os.path.exists(_src_ishihara) else _root_ishihara

    _src_questions = os.path.join(BASE_DIR, "src", "data", "questions.txt")
    _root_questions = os.path.join(BASE_DIR, "questions.txt")
    QUESTIONS_PATH = _src_questions if os.path.exists(_src_questions) else _root_questions

    # ── Upload ───────────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
