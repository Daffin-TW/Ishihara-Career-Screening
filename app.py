"""
app.py – Entry point aplikasi Flask
Ishihara Color Blindness & Career Screening
"""
import logging
from flask import Flask, render_template
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    """Factory function untuk membuat instance Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Jinja2 globals: expose Python built-ins yang dibutuhkan template ────
    app.jinja_env.globals.update(
        enumerate=enumerate,
        zip=zip,
        len=len,
        min=min,
        max=max,
        int=int,
        str=str,
        round=round,
    )

    # ── Daftarkan Blueprints ─────────────────────────────────────────────────
    from routes.main import main_bp
    from routes.screening import screening_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(screening_bp)

    # ── Pre-load model saat startup ──────────────────────────────────────────
    with app.app_context():
        try:
            from utils.predictor import load_model, is_model_loaded
            if not is_model_loaded():
                load_model(app.config)
                logger.info("Model berhasil dimuat saat startup.")
        except Exception as e:
            logger.error(f"Gagal memuat model saat startup: {e}")
            logger.warning("Aplikasi tetap berjalan tanpa model. Cek path di config.py.")

    # ── Custom Error Handlers ────────────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    return app


# ── Jalankan langsung ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
